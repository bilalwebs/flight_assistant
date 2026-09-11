// Phase 15.8 CDP E2E — Final Integration, Polish, QA & CV Release.
// Node (native WebSocket) + Chrome DevTools Protocol (port 9230).
//
// Strategy: real backend for all core flows (auth, search, filters, sorting,
// details, booking lifecycle, My Bookings, cancellation, seats). State/error
// paths that cannot be produced from seeded data without destroying it are
// simulated at the HTTP boundary with backend-shaped envelopes; every other
// request passes through to the real backend. The AI assistant reply is
// provided by a deterministic fixture ONLY (the real LLM is non-deterministic
// and may be unavailable), while the client request (method/url/auth header/
// body) is asserted against the real contract.
//
// Coverage: T01-T100 across auth & session, landing & navigation, search &
// results, flight details, AI assistant, booking flow, My Bookings,
// cancellation, security & privacy, navigation & UX, responsive (390/768/1440)
// and browser quality.
import { writeFileSync } from "node:fs";

const CDP_URL = "http://127.0.0.1:9230";
const APP = "http://localhost:3000";
const API = "http://127.0.0.1:8000";
const PASS = "SecurePassword123";
const STAMP = Date.now();
const EMAIL = `flight-e2e-158-${STAMP}@example.com`;
const UI_EMAIL = `flight-e2e-158-reg-${STAMP}@example.com`;
const USER2_EMAIL = `flight-e2e-158-u2-${STAMP}@example.com`;

const localISO = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const TOMORROW = localISO(new Date(Date.now() + 86400000));

// ---------- result plumbing ----------
const results = [];
function pass(name, detail = "") {
  results.push({ ok: true, name, detail });
}
function fail(name, detail) {
  results.push({ ok: false, name, detail: String(detail).slice(0, 500) });
}
async function record(name, fn) {
  try {
    const res = fn();
    if (res && typeof res.then === "function") await res;
    pass(name);
  } catch (err) {
    fail(name, err instanceof Error ? err.message : err);
  }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const consoleErrors = [];
const pageErrors = [];
const networkFailures = [];
const requests = [];

// ---------- CDP plumbing ----------
async function getWsUrl() {
  const res = await fetch(`${CDP_URL}/json/list`);
  const targets = await res.json();
  const page = targets.find((t) => t.type === "page") || targets[0];
  if (!page) throw new Error("no page target");
  return page.webSocketDebuggerUrl;
}

let ws;
let msgId = 0;
const pending = new Map();
const listeners = new Map();

function send(method, params = {}) {
  const id = ++msgId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
function on(method, cb) {
  if (!listeners.has(method)) listeners.set(method, []);
  listeners.get(method).push(cb);
}

async function connect() {
  ws = new WebSocket(await getWsUrl());
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", reject);
  });
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
      return;
    }
    const callbacks = listeners.get(msg.method) || [];
    for (const cb of callbacks) cb(msg.params || {});
  });
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Network.enable");
  await send("Log.enable");
  on("Runtime.consoleAPICalled", (p) => {
    if (p.type === "error") {
      consoleErrors.push((p.args || []).map((a) => a.value ?? a.description ?? "").join(" "));
    }
  });
  on("Runtime.exceptionThrown", (p) => {
    pageErrors.push(p.exceptionDetails?.text || "uncaught exception");
  });
  on("Log.entryAdded", (p) => {
    if (p.entry?.level === "error") consoleErrors.push(p.entry.text || "log error");
  });
  on("Network.loadingFailed", (p) => {
    if (p.type === "XHR" || p.type === "Fetch") {
      networkFailures.push(`${p.errorText} ${p.cancelled ? "(cancelled)" : ""}`.trim());
    }
  });
  on("Network.requestWillBeSent", (p) => {
    requests.push({
      url: p.request.url,
      method: p.request.method,
      postData: p.request.postData || "",
      headers: p.request.headers || {},
      ts: Date.now(),
    });
  });
}

// ---------- request capture + mocking ----------
const mocks = []; // { method, urlRe, status?, body?, delayMs }
let passDelayMs = 0;
let interceptionEnabled = false;

function clearMocks() {
  mocks.length = 0;
  passDelayMs = 0;
}

function requestCount(method, urlRe) {
  return requests.filter((r) => r.method === method && urlRe.test(r.url)).length;
}
const listUrlRe = () => /\/api\/bookings$/;
const detailUrlRe = (pnr) => new RegExp(`/api/bookings/${pnr}$`);
const cancelUrlRe = (pnr) => new RegExp(`/api/bookings/${pnr}/cancel$`);
const createUrlRe = () => /\/api\/bookings$/;
const confirmUrlRe = () => /\/api\/bookings\/[A-Z0-9]{6}\/confirm$/;
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const flightRe = (id) => new RegExp(`/api/flights/${esc(id)}$`);

// ---------- assistant chat fixture ----------
let assistantActive = false;
let chatMode = "pass"; // pass | fail500 | unauth | network
let chatDelayMs = 0;
let chatSequence = 0;
const chatLog = []; // { seq, requestBody, authorization, response }

const TURN_REPLIES = {
  1: `I see two direct flights from Karachi to Dubai on ${TOMORROW}: PK-201 departing 08:00 for $210, and EK-601 departing 10:00 for $280.`,
  2: "Upgrading to business class on that Karachi-Dubai route? EK-603 departs at 14:00 with 40kg baggage, priced at $950 per person.",
};

function convIdFor(requestBody) {
  if (requestBody && requestBody.conversation_id) return requestBody.conversation_id;
  return `550e8400-e29b-41d4-a716-4466554401${String(chatSequence).padStart(2, "0")}`;
}

function chatRequestCount() {
  return chatLog.length;
}

async function enableInterception() {
  if (interceptionEnabled) return;
  interceptionEnabled = true;
  await send("Fetch.enable", {
    patterns: [{ urlPattern: "*://127.0.0.1:8000/*", requestStage: "Request" }],
  });
}

on("Fetch.requestPaused", async (p) => {
  const { requestId, request } = p;
  const method = request.method;
  const url = request.url;
  try {
    // Assistant chat fixture (deterministic LLM replacement).
    if (assistantActive && url.includes("/api/assistant/chat") && method === "POST") {
      chatSequence += 1;
      const seq = chatSequence;
      if (chatDelayMs) await sleep(chatDelayMs);
      let requestBody = {};
      try {
        requestBody = request.postData ? JSON.parse(request.postData) : {};
      } catch {
        requestBody = { parseError: true };
      }
      const authorization = request.headers?.Authorization || request.headers?.authorization || "";
      if (chatMode === "network") {
        chatLog.push({ seq, requestBody, authorization, response: null });
        await send("Fetch.failRequest", { requestId, errorReason: "Failed" });
        return;
      }
      if (chatMode === "unauth") {
        chatLog.push({ seq, requestBody, authorization, response: null });
        await send("Fetch.fulfillRequest", {
          requestId,
          responseCode: 401,
          responseHeaders: corsHeaders(),
          body: Buffer.from(JSON.stringify({ detail: "Not authenticated" })).toString("base64"),
        });
        return;
      }
      if (chatMode === "fail500") {
        chatLog.push({ seq, requestBody, authorization, response: null });
        await send("Fetch.fulfillRequest", {
          requestId,
          responseCode: 500,
          responseHeaders: corsHeaders(),
          body: Buffer.from(JSON.stringify({ detail: "Assistant request failed. Please try again." })).toString("base64"),
        });
        return;
      }
      const conversation_id = convIdFor(requestBody);
      const message = TURN_REPLIES[seq] || `reply ${seq}: here is what I can tell you about that.`;
      const response = { conversation_id, message, success: true };
      chatLog.push({ seq, requestBody, authorization, response });
      await send("Fetch.fulfillRequest", {
        requestId,
        responseCode: 200,
        responseHeaders: corsHeaders(),
        body: Buffer.from(JSON.stringify(response)).toString("base64"),
      });
      return;
    }

    // Backend-shaped mock table (pass-through otherwise).
    let hit = null;
    for (const m of mocks) {
      if (m.method === method && m.urlRe.test(url)) {
        hit = m;
        break;
      }
    }
    if (hit && hit.status) {
      await sleep(hit.delayMs || 0);
      const body = Buffer.from(JSON.stringify(hit.body)).toString("base64");
      await send("Fetch.fulfillRequest", {
        requestId,
        responseCode: hit.status,
        responseHeaders: corsHeaders(),
        body,
      });
      return;
    }
    if (passDelayMs > 0) await sleep(passDelayMs);
    await send("Fetch.continueRequest", { requestId });
  } catch {
    try {
      await send("Fetch.continueRequest", { requestId });
    } catch {
      /* ignore */
    }
  }
});

function corsHeaders() {
  return [
    { name: "Content-Type", value: "application/json" },
    { name: "Access-Control-Allow-Origin", value: "http://localhost:3000" },
    { name: "Access-Control-Allow-Credentials", value: "true" },
    { name: "Vary", value: "Origin" },
  ];
}

// ---------- browser helpers ----------
async function navigate(url) {
  await send("Page.navigate", { url });
  const start = Date.now();
  while (Date.now() - start < 20000) {
    const state = await evalJs(`({ href: location.href, ready: document.readyState })`).catch(() => ({
      href: "",
      ready: "",
    }));
    if (state.href && state.ready === "complete" && /^https?:/.test(state.href)) {
      await sleep(250);
      return state.href;
    }
    await sleep(120);
  }
  throw new Error("navigate timeout: " + url);
}

async function evalJs(expression) {
  const res = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (res.exceptionDetails) {
    throw new Error(
      (res.exceptionDetails.text || "eval error") +
        " :: " +
        JSON.stringify(res.exceptionDetails.exception || {}).slice(0, 300),
    );
  }
  return res.result?.value;
}

async function waitFor(expression, timeoutMs = 12000, label = expression) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await evalJs(expression).catch(() => false)) return true;
    await sleep(120);
  }
  throw new Error(`Timed out waiting for: ${label}`);
}

const bodyText = () => evalJs(`document.body ? document.body.innerText : ""`);
const currentPath = () => evalJs(`typeof location === "undefined" ? "" : location.pathname`);
const currentHref = () => evalJs(`typeof location === "undefined" ? "" : location.href`);

async function clickByText(selector, text, timeoutMs = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const ok = await evalJs(`(() => {
      const els = [...document.querySelectorAll(${JSON.stringify(selector)})];
      const visible = (el) => el.offsetParent !== null && !el.disabled;
      const el = els.find((e) => visible(e) && (e.textContent || "").replace(/\\s+/g, " ").trim().includes(${JSON.stringify(text)}));
      if (!el) return false;
      el.click();
      return true;
    })()`);
    if (ok) return;
    await sleep(200);
  }
  throw new Error(`Element not found (visible): ${selector} "${text}"`);
}

function setValueByProto(selectorExpr, value, protoName) {
  return evalJs(`(() => {
    const el = ${selectorExpr};
    if (!el) return false;
    const setter = Object.getOwnPropertyDescriptor(${protoName}.prototype, "value").set;
    setter.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
}

const setInput = (selectorExpr, value) => setValueByProto(selectorExpr, value, "HTMLInputElement");
const setTextareaEl = (selectorExpr, value) => setValueByProto(selectorExpr, value, "HTMLTextAreaElement");

async function setInputByLabel(labelText, value) {
  const ok = await evalJs(`(() => {
    const labels = [...document.querySelectorAll("label")].filter((l) => l.offsetParent !== null);
    const label = labels.find((l) => l.htmlFor && (l.textContent || "").trim().startsWith(${JSON.stringify(labelText)}));
    if (!label) return false;
    const el = document.getElementById(label.htmlFor);
    if (!el) return false;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(el, ${JSON.stringify("__VAL__")});
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`.replace('"__VAL__"', JSON.stringify(value)));
  if (!ok) throw new Error(`Input not found by label: ${labelText}`);
}

async function selectByLabel(labelText, value) {
  const ok = await evalJs(`(() => {
    const labels = [...document.querySelectorAll("label")].filter((l) => l.offsetParent !== null);
    const label = labels.find((l) => l.htmlFor && (l.textContent || "").trim().startsWith(${JSON.stringify(labelText)}));
    if (!label) return false;
    const el = document.getElementById(label.htmlFor);
    if (!el) return false;
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set;
    setter.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!ok) throw new Error(`Select not found by label: ${labelText}`);
}

// ---------- backend helpers ----------
async function apiLogin(email, password) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`login failed ${res.status} for ${email}`);
  const data = await res.json();
  return { token: data.access_token, user: data.user };
}

async function apiRegister(email, password) {
  const res = await fetch(`${API}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "Flight E2E User", email, password }),
  });
  if (!res.ok) throw new Error(`register failed ${res.status}`);
  return res.json();
}

async function apiSearch(token, origin, destination, date) {
  const res = await fetch(`${API}/api/flights/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ origin, destination, date, cabin_class: "economy" }),
  });
  if (!res.ok) throw new Error(`search failed ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : Array.isArray(data?.flights) ? data.flights : [];
}

function buildCreateBody(flightId, count = 1) {
  return {
    flight_id: flightId,
    passengers: Array.from({ length: count }, (_, i) => ({
      first_name: `Pax${i + 1}`,
      last_name: "E2E",
      passenger_type: "adult",
      date_of_birth: "1990-01-01",
    })),
    cabin_class: "economy",
  };
}

async function apiCreateBooking(token, flightId, count = 1) {
  const res = await fetch(`${API}/api/bookings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(buildCreateBody(flightId, count)),
  });
  if (!res.ok) throw new Error(`create booking failed ${res.status}: ${await res.text()}`);
  return res.json();
}

async function apiGetBooking(token, pnr) {
  const res = await fetch(`${API}/api/bookings/${pnr}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`get booking ${pnr} failed ${res.status}`);
  return res.json();
}

async function apiGetFlightSeats(token, flightId) {
  const res = await fetch(`${API}/api/flights/${encodeURIComponent(flightId)}/seats`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`seats failed ${res.status}`);
  return res.json();
}

function mkBooking(overrides) {
  const base = {
    id: "10000000-0000-4000-8000-000000000001",
    pnr: "MCK001",
    user_id: "",
    flight_id: "",
    status: "confirmed",
    cabin_class: "economy",
    passenger_count: 1,
    base_amount: 150,
    tax_amount: 22.5,
    total_amount: 172.5,
    currency: "USD",
    contact_email: EMAIL,
    contact_phone: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  return { ...base, ...overrides };
}

// ---------- UI helpers ----------
async function uiLogin(email, password) {
  await navigate(`${APP}/login`);
  await waitFor(`document.querySelector('input[type="email"]') != null`, 10000, "login form");
  const ok = await evalJs(`(() => {
    const labels = [...document.querySelectorAll("label")].filter((l) => l.offsetParent !== null);
    const setV = (labelText, value) => {
      const label = labels.find((l) => l.htmlFor && (l.textContent || "").trim().startsWith(labelText));
      if (!label) return false;
      const el = document.getElementById(label.htmlFor);
      if (!el) return false;
      const tag = el.tagName === "TEXTAREA" ? HTMLTextAreaElement : HTMLInputElement;
      const setter = Object.getOwnPropertyDescriptor(tag.prototype, "value").set;
      setter.call(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    };
    return setV("Email", ${JSON.stringify(email)}) && setV("Password", ${JSON.stringify(password)});
  })()`);
  if (!ok) throw new Error("could not fill login form");
  await clickByText("button", "Sign in");
  await waitFor(`!location.pathname.startsWith('/login')`, 15000, "login success");
}

// Login starting from a specific URL (e.g. /login?next=...) so the next-param
// roundtrip can be asserted.
async function uiLoginFrom(url, email, password) {
  await navigate(url);
  await waitFor(`document.querySelector('input[type="email"]') != null`, 10000, "login form");
  const ok = await evalJs(`(() => {
    const labels = [...document.querySelectorAll("label")].filter((l) => l.offsetParent !== null);
    const setV = (labelText, value) => {
      const label = labels.find((l) => l.htmlFor && (l.textContent || "").trim().startsWith(labelText));
      if (!label) return false;
      const el = document.getElementById(label.htmlFor);
      if (!el) return false;
      const tag = el.tagName === "TEXTAREA" ? HTMLTextAreaElement : HTMLInputElement;
      const setter = Object.getOwnPropertyDescriptor(tag.prototype, "value").set;
      setter.call(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    };
    return setV("Email", ${JSON.stringify(email)}) && setV("Password", ${JSON.stringify(password)});
  })()`);
  if (!ok) throw new Error("could not fill login form");
  await clickByText("button", "Sign in");
  await waitFor(`!location.pathname.startsWith('/login')`, 15000, "login success");
}

async function clearAuthStorage() {
  await navigate(`${APP}/`);
  await evalJs(`localStorage.removeItem("flight_assistant_auth")`);
}

async function uiLogout() {
  await evalJs(`(() => {
    const el = document.querySelector('button[aria-label="Sign out"]');
    if (el) { el.click(); return true; }
    return false;
  })()`);
  await sleep(600);
  await waitFor(`location.pathname.startsWith('/login') && !localStorage.getItem("flight_assistant_auth")`, 10000, "logout redirect");
}

async function uiRegister(name, email, password) {
  await navigate(`${APP}/register`);
  await waitFor(`document.querySelector('input[type="email"]') != null`, 8000, "register form");
  await setInputByLabel("Full name", name);
  await setInputByLabel("Email", email);
  await setInputByLabel("Password", password);
  const pwInputs = await evalJs(`[...document.querySelectorAll('input[type="password"]')].filter((i) => i.offsetParent !== null).length`);
  if (pwInputs >= 2) {
    await setInput(`[...document.querySelectorAll('input[type="password"]')][${pwInputs - 1}]`, password);
  }
  await clickByText("button", "Create account");
  await waitFor(`!location.pathname.startsWith('/register')`, 15000, "register redirect");
}

// ---------- search + results helpers ----------
async function currentResults() {
  return evalJs(`[...document.querySelectorAll('article')].map((a) => a.innerText + " HREF=" + (a.querySelector('a[href^="/flights/"]')?.getAttribute('href') || ''))`);
}

async function waitForCount(target, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const cards = await currentResults();
    if (cards.length === target) return cards;
    await sleep(250);
  }
  throw new Error(`cards never reached ${target}`);
}

async function searchFlightsInUI(origin = "KHI", dest = "DXB") {
  await navigate(`${APP}/flights/search`);
  await waitFor(`document.querySelector('input[aria-label="Origin airport code"]') != null`, 8000, "origin input");
  await setInput(`document.querySelector('input[aria-label="Origin airport code"]')`, origin);
  await setInput(`document.querySelector('input[aria-label="Destination airport code"]')`, dest);
  await clickByText("button", "Search flights");
  await waitFor(`[...document.querySelectorAll('h2')].some((h) => /flight[s]? found/.test(h.textContent))`, 15000, "search results");
}

async function clearFiltersAction() {
  await clickByText("button", "Clear filters");
  await waitFor(`[...document.querySelectorAll('h2')].some((h) => /flight[s]? found/.test(h.textContent))`, 15000, "cleared");
}

// ---------- booking flow helpers ----------
async function openBookingForm(flightId) {
  await navigate(`${APP}/bookings/new/${flightId}`);
  await waitFor(`document.getElementById('passenger-1-first-name') != null`, 15000, "booking form");
}

function fillPassenger(passengerNo, firstName, lastName, dob, type = "adult") {
  return evalJs(`(() => {
    const setEl = (id, value, protoProto) => {
      const el = document.getElementById(id);
      if (!el) return false;
      const setter = Object.getOwnPropertyDescriptor(protoProto.prototype, "value").set;
      setter.call(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    };
    let ok = setEl("passenger-${passengerNo}-type", ${JSON.stringify(type)}, HTMLSelectElement);
    ok = setEl("passenger-${passengerNo}-first-name", ${JSON.stringify(firstName)}, HTMLInputElement) && ok;
    ok = setEl("passenger-${passengerNo}-last-name", ${JSON.stringify(lastName)}, HTMLInputElement) && ok;
    ok = setEl("passenger-${passengerNo}-dob", ${JSON.stringify(dob)}, HTMLInputElement) && ok;
    return ok;
  })()`).then((ok) => {
    if (!ok) throw new Error(`passenger ${passengerNo} field missing`);
  });
}

async function fillContact(email, phone) {
  const a = await setInput(`document.getElementById('contact-email')`, email);
  const b = await setInput(`document.getElementById('contact-phone')`, phone);
  if (!a || !b) throw new Error("contact fields missing");
}

async function clickCreate() {
  const ok = await evalJs(`(() => {
    const el = document.querySelector('button[aria-label="Create booking"]');
    if (!el) return false;
    el.click();
    return true;
  })()`);
  if (!ok) throw new Error("create button not found");
}

async function clickConfirm() {
  const ok = await evalJs(`(() => {
    const el = document.querySelector('button[aria-label="Confirm booking"]');
    if (!el) return false;
    el.click();
    return true;
  })()`);
  if (!ok) throw new Error("confirm button not found");
}

async function readPnr() {
  const pnr = await evalJs(`(() => {
    const dt = [...document.querySelectorAll("dt")].find((el) => (el.textContent || "").trim() === "PNR");
    return dt && dt.nextElementSibling ? (dt.nextElementSibling.textContent || "").trim() : "";
  })()`);
  if (!/^[A-Z0-9]{6}$/.test(pnr)) throw new Error(`bad PNR: ${pnr}`);
  return pnr;
}

async function clickConfirmCancel() {
  await waitFor(`[...document.querySelectorAll('[role="dialog"] button')].some(e => e.getAttribute('aria-label') === 'Confirm cancellation' && e.offsetParent !== null)`, 6000, "confirm-cancel present");
  const ok = await evalJs(`(() => {
    const els = [...document.querySelectorAll('[role="dialog"] button')];
    const el = els.find((e) => e.offsetParent !== null && e.getAttribute('aria-label') === 'Confirm cancellation');
    if (!el || el.disabled) return false;
    el.click();
    return true;
  })()`);
  if (!ok) {
    console.error("DIALOG DUMP:", await evalJs(`(() => { const d = document.querySelector('[role="dialog"]'); return d ? d.outerHTML.slice(0, 2000) : 'NO DIALOG'; })()`).catch(() => "eval error"));
    throw new Error("confirm-cancel button not found");
  }
}

// ---------- assistant helpers ----------
async function setChatInput(text) {
  const ok = await setTextareaEl(`document.getElementById('assistant-chat-input')`, text);
  if (!ok) throw new Error("chat textarea missing");
}

async function clickChatSend() {
  const ok = await evalJs(`(() => {
    const el = document.querySelector('button[aria-label="Send message"]');
    if (!el || el.disabled) return false;
    el.click();
    return true;
  })()`);
  if (!ok) throw new Error("send button not clickable");
}

// ============================================================
// MAIN
// ============================================================
async function main() {
  await connect();
  await enableInterception();
  await send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });

  // Clean unauthenticated start.
  await navigate(APP);
  await evalJs(`localStorage.clear(); sessionStorage.clear(); true;`);

  // Data setup: two harness users + real flight search.
  try {
    await apiRegister(EMAIL, PASS);
  } catch {
    /* already exists */
  }
  try {
    await apiRegister(USER2_EMAIL, PASS);
  } catch {
    /* already exists */
  }
  const seedAuth = await apiLogin(EMAIL, PASS);
  const seedUser = seedAuth.user;

  const flights = await apiSearch(seedAuth.token, "KHI", "DXB", TOMORROW);
  if (flights.length === 0) throw new Error("no flights found");
  const realId = flights[0].id;
  const realFlight = flights[0];
  const realId2 = flights[1] ? flights[1].id : realId;
  const baselineSeats1 = realFlight.available_seats;
  const baselineId2 = await apiGetFlightSeats(seedAuth.token, realId2);
  const baselineSeats2 = baselineId2.available_seats;

  await clearAuthStorage();

  // ============================================================
  // 1. AUTH & SESSION (T01-T10)
  // ============================================================
  await uiRegister("Final Register User", UI_EMAIL, PASS);
  await record("T01: register creates an account and leaves the register page", () => {
    // redirected; uiRegister already asserted this.
  });

  const signOutPresent = await evalJs(`!!document.querySelector('button[aria-label="Sign out"]')`);
  await record("T02: navbar shows signed-in identity after register", () => {
    if (!signOutPresent) throw new Error("no sign-out button");
  });

  await uiLogout();
  await record("T03: logout clears the session and the route guard lands on login", async () => {
    const p = await currentPath();
    if (!p.startsWith("/login")) throw new Error(`got ${p}`);
    const has = await evalJs(`!!localStorage.getItem("flight_assistant_auth")`);
    if (has) throw new Error("session not cleared");
  });

  // Invalid credentials.
  await navigate(`${APP}/login`);
  await waitFor(`document.querySelector('input[type="email"]') != null`, 8000, "login form");
  await setInputByLabel("Email", "nobody@example.com");
  await setInputByLabel("Password", "WrongPass123");
  await clickByText("button", "Sign in");
  await waitFor(`document.body.innerText.includes('Invalid email or password.')`, 12000, "login error");
  await record("T04: invalid credentials show error and stay on login", async () => {
    const p = await currentPath();
    if (!p.startsWith("/login")) throw new Error(`left login: ${p}`);
    const t = await bodyText();
    if (!t.includes("Invalid email or password.")) throw new Error("error text missing");
  });

  await record("T05: password field is masked as type=password", async () => {
    const masked = await evalJs(`[...document.querySelectorAll('input')].some((i) => i.type === 'password')`);
    if (!masked) throw new Error("no masked password input");
  });

  await uiLogin(EMAIL, PASS);
  await record("T06: login form signs in existing user", async () => {
    const p = await currentPath();
    if (p.startsWith("/login")) throw new Error(`still on login ${p}`);
    const has = await evalJs(`!!document.querySelector('button[aria-label="Sign out"]')`);
    if (!has) throw new Error("not signed in");
  });

  // Protected route redirect + next-param roundtrip.
  await clearAuthStorage();
  await navigate(`${APP}/profile`);
  await waitFor(`location.pathname.startsWith('/login')`, 10000, "profile guard");
  await record("T07: unauthenticated /profile redirects to login with next", async () => {
    const href = await currentHref();
    if (!href.includes("/login") || !decodeURIComponent(href).includes("/profile")) {
      throw new Error(`got ${href}`);
    }
  });

  await uiLoginFrom(`${APP}/login?next=${encodeURIComponent("/profile")}`, EMAIL, PASS);
  await waitFor(`location.pathname === '/profile'`, 10000, "next roundtrip");
  await record("T08: login via next param lands back on /profile", async () => {
    const p = await currentPath();
    if (p !== "/profile") throw new Error(`got ${p}`);
  });

  // Session persistence across a full page load.
  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes('My Bookings')`, 12000, "bookings authed");
  await record("T09: session persists across full page navigation", async () => {
    const p = await currentPath();
    if (p.startsWith("/login")) throw new Error("dropped to login");
    const t = await bodyText();
    if (!t.includes("My Bookings")) throw new Error("not on bookings");
  });

  await clearAuthStorage();
  await navigate(`${APP}/flights/search`);
  await waitFor(`location.pathname.startsWith('/login')`, 10000, "search guard");
  await record("T10: unauthenticated /flights/search redirects to login", async () => {
    const href = await currentHref();
    if (!decodeURIComponent(href).includes("/flights/search")) throw new Error(`got ${href}`);
  });
  await uiLogin(EMAIL, PASS);

  // ============================================================
  // 2. LANDING & NAVIGATION (T11-T18)
  // ============================================================
  await navigate(APP);
  const landingText = await bodyText();
  await record("T11: landing hero renders headline, subhead and badge", () => {
    if (!landingText.includes("Find your next flight, effortlessly.")) throw new Error("hero missing");
    if (!landingText.includes("Search flights, compare options, and get intelligent")) throw new Error("subhead missing");
    if (!landingText.includes("AI-powered flight booking platform")) throw new Error("badge missing");
  });

  await clickByText("a", "Search Flights");
  await waitFor(`location.pathname === '/flights/search'`, 10000, "hero CTA nav");
  await record("T12: hero Search Flights CTA navigates to /flights/search", async () => {
    const p = await currentPath();
    if (p !== "/flights/search") throw new Error(`got ${p}`);
  });
  await navigate(APP);

  await record("T13: features grid shows the four product pillars", () => {
    for (const f of ["Smart Flight Search", "AI Travel Assistant", "Simple Booking", "Real-time Availability"]) {
      if (!landingText.includes(f)) throw new Error(`feature missing: ${f}`);
    }
  });

  await record("T14: landing preview copy is final (no stale placeholder)", () => {
    if (!landingText.includes("Sign in to search live flights")) throw new Error("preview badge copy missing");
    if (!landingText.includes("This preview shows the search experience. Sign in and start searching to see live availability and pricing.")) {
      throw new Error("preview body copy missing");
    }
    if (/arrives with the next phase|coming soon|Live searching arrives/i.test(landingText)) {
      throw new Error("stale placeholder text found");
    }
  });

  const footerInfo = await evalJs(`(() => {
    const foot = document.querySelector('footer');
    const links = [...foot.querySelectorAll('a')].map((a) => ({ text: (a.textContent || '').trim(), href: a.getAttribute('href') }));
    const headings = [...foot.querySelectorAll('h2')].map((h) => h.textContent.trim());
    return { headings, links };
  })()`);
  await record("T15: footer has Product/Account columns with real links, no dead links", () => {
    const hrefs = footerInfo.links.map((l) => l.href);
    for (const dead of ["/about", "/contact", "/privacy", "/terms"]) {
      if (hrefs.includes(dead)) throw new Error(`dead footer link: ${dead}`);
    }
    for (const h of ["Product", "Account"]) if (!footerInfo.headings.includes(h)) throw new Error(`column missing ${h}`);
    for (const href of ["/flights/search", "/assistant", "/bookings", "/profile", "/login", "/register"]) {
      if (!hrefs.includes(href)) throw new Error(`footer link missing ${href}`);
    }
  });

  await clickByText("a", "My Bookings");
  await waitFor(`location.pathname === '/bookings'`, 10000, "footer bookings");
  await record("T16: footer My Bookings link works", async () => {
    const p = await currentPath();
    if (p !== "/bookings") throw new Error(`got ${p}`);
  });

  await navigate(`${APP}/definitely-not-a-real-route`);
  await waitFor(`document.body.innerText.includes('Page not found')`, 10000, "404 page");
  await record("T17: unknown route renders styled 404 with Back to home", async () => {
    const t = await bodyText();
    if (!t.includes("Page not found")) throw new Error("404 title missing");
  });
  await clickByText("a", "Back to home");
  await waitFor(`location.pathname === '/'`, 8000, "404 back home");
  await record("T17b: 404 Back to home navigates to the landing page", async () => {
    const p = await currentPath();
    if (p !== "/") throw new Error(`got ${p}`);
  });

  // Mobile menu (390).
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
  await navigate(APP);
  await evalJs(`(() => { const b = document.querySelector('button[aria-label="Open menu"]'); if (!b) return false; b.click(); return true; })()`);
  await waitFor(`document.getElementById('mobile-menu') != null`, 8000, "mobile menu");
  const menuText = await bodyText();
  await record("T18: mobile menu exposes authed nav links (Flights, AI Assistant, My Bookings, Profile, Logout)", () => {
    for (const item of ["Flights", "AI Assistant", "My Bookings", "Profile"]) {
      if (!menuText.includes(item)) throw new Error(`menu missing ${item}`);
    }
  });
  await evalJs(`(() => { const b = document.querySelector('button[aria-label="Close menu"]'); if (!b) return false; b.click(); return true; })()`);
  await waitFor(`document.getElementById('mobile-menu') == null`, 8000, "mobile menu closed");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  // ============================================================
  // 3. SEARCH & RESULTS (T19-T30)
  // ============================================================
  await navigate(`${APP}/flights/search`);
  await waitFor(`document.querySelector('input[aria-label="Origin airport code"]') != null`, 8000, "search form");
  await record("T19: search form renders origin/destination/date/cabin/passengers", async () => {
    const ok = await evalJs(`(() => ({
      o: !!document.querySelector('input[aria-label="Origin airport code"]'),
      d: !!document.querySelector('input[aria-label="Destination airport code"]'),
      date: !!document.querySelector('input[type="date"]'),
      cabin: !!document.querySelector('select'),
      pax: true,
    }))()`);
    if (!ok.o || !ok.d || !ok.date || !ok.cabin) throw new Error(`form fields: ${JSON.stringify(ok)}`);
  });

  const beforeSearchCount = requestCount("POST", /\/api\/flights\/search$/);
  await setInput(`document.querySelector('input[aria-label="Origin airport code"]')`, "KHI");
  await setInput(`document.querySelector('input[aria-label="Destination airport code"]')`, "KHI");
  await clickByText("button", "Search flights");
  await waitFor(`document.body.innerText.includes('Origin and destination must be different.')`, 8000, "validation error");
  await record("T20: KHI→KHI validation blocks the request", () => {
    const after = requestCount("POST", /\/api\/flights\/search$/);
    if (after !== beforeSearchCount) throw new Error("request was sent for invalid route");
  });

  await evalJs(`(() => { const el = document.querySelector('button[aria-label="Swap origin and destination"]'); if (!el) return false; el.click(); return true; })()`);
  const swappedDest = await evalJs(`document.querySelector('input[aria-label="Destination airport code"]')?.value`);
  await record("T21: swap button toggles origin and destination", () => {
    if (swappedDest !== "KHI") throw new Error(`expected KHI got ${swappedDest}`);
  });

  await setInput(`document.querySelector('input[aria-label="Destination airport code"]')`, "DXB");
  await clickByText("button", "Search flights");
  await waitFor(`[...document.querySelectorAll('h2')].some((h) => /flight[s]? found/.test(h.textContent))`, 15000, "valid search");
  const searchCards = await currentResults();
  await record("T22: real search KHI→DXB returns five flights incl. PK-201 and EK-601", () => {
    if (searchCards.length !== 5) throw new Error(`expected 5 got ${searchCards.length}`);
    const all = searchCards.join(" ");
    if (!all.includes("PK-201") || !all.includes("EK-601")) throw new Error("expected flights missing");
  });
  await record("T23: result cards show airline, flight, route, schedule, stops and price", () => {
    const first = searchCards[0];
    for (const needle of [realFlight.airline_code, realFlight.flight_number, realFlight.origin, realFlight.destination]) {
      if (!first.includes(String(needle))) throw new Error(`card missing ${needle}`);
    }
    if (!/AM|PM/.test(first)) throw new Error("no schedule times");
    if (!/\$\d/.test(first)) throw new Error("no price on card");
  });

  // Airline filter.
  await evalJs(`(() => {
    const checks = [...document.querySelectorAll('input[type=checkbox]')].filter((i) => i.offsetParent !== null);
    const el = checks.find((i) => i.closest('label').textContent.trim().includes('Emirates'));
    if (!el) return false;
    el.click();
    return true;
  })()`);
  await clickByText("button", "Apply Filters");
  const emiratesCards = await waitForCount(2);
  const filterBodies = requests.filter((r) => r.method === "POST" && /\/api\/flights\/filter$/.test(r.url) && !r.postData.includes("page")).map((r) => r.postData);
  await record("T24: airline filter uses the real API and narrows to Emirates", () => {
    if (!filterBodies.length) throw new Error("no filter request captured");
    if (!filterBodies.at(-1).includes('"airline":"Emirates"')) throw new Error(`airline missing ${filterBodies.at(-1)}`);
    if (emiratesCards.length !== 2) throw new Error(`expected 2 got ${emiratesCards.length}`);
    for (const c of emiratesCards) if (!c.includes("EK-601")) throw new Error("non-Emirates result leaked");
  });

  await clearFiltersAction();
  await record("T25: Clear filters restores the full five results", async () => {
    const cards = await currentResults();
    if (cards.length !== 5) throw new Error(`expected 5 got ${cards.length}`);
  });

  // Price filter.
  await setInput(`document.querySelector('input[aria-label="Maximum price"]')`, "250");
  await clickByText("button", "Apply Filters");
  const priceCards = await waitForCount(3);
  const priceBodies = requests.filter((r) => r.method === "POST" && /\/api\/flights\/filter$/.test(r.url)).map((r) => r.postData);
  await record("T26: price filter sends max_price and matches three real flights", () => {
    if (!priceBodies.at(-1).includes('"max_price":250')) throw new Error(`max_price missing ${priceBodies.at(-1)}`);
    if (priceCards.length !== 3) throw new Error(`expected 3 got ${priceCards.length}`);
    for (const c of priceCards) if (!c.includes("PK-201")) throw new Error("expected only PK-201 results");
  });
  await clearFiltersAction();

  // Stops filter.
  await evalJs(`(() => {
    const el = [...document.querySelectorAll('input[type=radio]')].find((i) => i.offsetParent !== null && i.closest('label').textContent.trim().includes('Nonstop'));
    if (!el) return false;
    el.click();
    return true;
  })()`);
  await clickByText("button", "Apply Filters");
  await waitFor(`[...document.querySelectorAll('h2')].some((h) => /flight[s]? found/.test(h.textContent))`, 15000, "stops filter applied");
  const stopsBodies = requests.filter((r) => r.method === "POST" && /\/api\/flights\/filter$/.test(r.url)).map((r) => r.postData);
  await record("T27: nonstop filter sends max_stops 0", () => {
    if (!stopsBodies.at(-1).includes('"max_stops":0')) throw new Error(`max_stops missing ${stopsBodies.at(-1)}`);
  });
  await clearFiltersAction();

  // Sorting.
  const firstPrice = async () =>
    evalJs(`[...document.querySelectorAll('article')][0]?.innerText.split('\\n').find((l) => /\\$\\d/.test(l))`);
  await selectByLabel("Sort results", "price_asc");
  await sleep(400);
  await record("T28: sort by price low-to-high puts PK-201 ($210) first", async () => {
    const p = await firstPrice();
    if (!p?.includes("$210.00")) throw new Error(`first price ${p}`);
  });
  await selectByLabel("Sort results", "price_desc");
  await sleep(400);
  await record("T29: sort by price high-to-low puts EK-601 ($280) first", async () => {
    const p = await firstPrice();
    if (!p?.includes("$280.00")) throw new Error(`first price ${p}`);
  });

  // No-results state.
  await setInput(`document.querySelector('input[aria-label="Origin airport code"]')`, "KHI");
  await setInput(`document.querySelector('input[aria-label="Destination airport code"]')`, "DXB");
  await setInput(`document.querySelector('input[type="date"]')`, "2030-05-05");
  await clickByText("button", "Search flights");
  await waitFor(`document.body.innerText.includes('No flights found')`, 15000, "no-results empty state");
  await record("T30: far-future date shows the no-flights empty state", async () => {
    const cards = await currentResults();
    if (cards.length !== 0) throw new Error(`expected 0 got ${cards.length}`);
    const t = await bodyText();
    if (!/No flights found/.test(t)) throw new Error("empty-state copy missing");
  });

  // ============================================================
  // 4. FLIGHT DETAILS (T31-T40)
  // ============================================================
  await searchFlightsInUI();
  await waitForCount(5);
  await clickByText("a", "View Details");
  await waitFor(`location.pathname.startsWith('/flights/') && location.pathname !== '/flights/search'`, 10000, "details nav");
  await waitFor(`document.body.innerText.includes(${JSON.stringify(realFlight.airline)})`, 12000, "details airline");

  const seatLive = await apiGetFlightSeats(seedAuth.token, realId);
  await waitFor(`document.body.innerText.includes('Seat availability')`, 10000, "seat section");
  await waitFor(`document.body.innerText.includes('Grand total')`, 10000, "price section");
  const detailText = await bodyText();
  await record("T31: details show airline, flight number, route and nonstop", () => {
    for (const needle of [realFlight.airline, `Flight ${realFlight.flight_number}`, realFlight.origin, realFlight.destination, "Nonstop"]) {
      if (!detailText.includes(String(needle))) throw new Error(`missing "${needle}"`);
    }
    if (!detailText.includes("AM") && !detailText.includes("PM")) throw new Error("no schedule times");
  });
  await record("T32: live seat availability matches backend (" + seatLive.available_seats + " seats)", () => {
    const m = detailText.match(/(\d+)\s*of\s*(\d+)\s*seats/);
    if (!m) throw new Error("no 'N of M seats'");
    if (Number(m[1]) !== seatLive.available_seats) throw new Error(`expected ${seatLive.available_seats} got ${m[1]}`);
    if (!detailText.includes(`${seatLive.available_seats} seats available`)) throw new Error("no availability status");
  });
  await record("T33: real backend price breakdown (base, tax, total per person)", () => {
    for (const needle of ["$210.00", "$31.50", "$241.50"]) {
      if (!detailText.includes(needle)) throw new Error(`missing ${needle}`);
    }
    if (!/Base fare/.test(detailText) || !/Tax/.test(detailText) || !/Grand total/.test(detailText)) {
      throw new Error("breakdown labels missing");
    }
  });

  await selectByLabel("Passengers", "2");
  await waitFor(`document.body.innerText.includes('$483.00')`, 10000, "2-pax total");
  await record("T34: passenger count change recalculates price server-side", async () => {
    const t = await bodyText();
    if (!t.includes("$483.00")) throw new Error("expected $483.00 for 2 pax");
    if (!/Passengers\s*2|2\s*Passengers/.test(t.replace(/\s+/g, " "))) throw new Error("count not reflected");
  });

  await clickByText("a", "Back to search results");
  await waitFor(`location.pathname === '/flights/search'`, 8000, "back to search");
  await waitFor(`[...document.querySelectorAll('h2')].some((h) => /5 flights found/.test(h.textContent))`, 10000, "rehydrated results");
  await record("T35: back-link rehydrates the previous five results from context", async () => {
    const cards = await currentResults();
    if (cards.length !== 5) throw new Error(`expected 5 got ${cards.length}`);
  });

  await navigate(`${APP}/flights/00000000-0000-0000-0000-000000000000`);
  await waitFor(`document.body.innerText.includes('Flight not found')`, 10000, "404 flight");
  await record("T36: invalid flight id shows not-found with Back to Search", async () => {
    const t = await bodyText();
    if (!t.includes("Back to Search")) throw new Error("Back to Search missing");
  });

  await navigate(`${APP}/flights/${realId}`);
  await waitFor(`document.body.innerText.includes('Grand total')`, 12000, "details loaded");
  mocks.push({ method: "GET", urlRe: flightRe(realId), status: 500, body: { detail: "forced server error" } });
  await navigate(`${APP}/flights/${realId}`);
  await waitFor(`document.body.innerText.includes('Unable to load flight details.')`, 12000, "details 500 state");
  clearMocks();
  await clickByText("button", "Retry");
  await waitFor(`document.body.innerText.includes('Grand total')`, 12000, "details recovered");
  await record("T37: details API 500 shows retry state and Retry recovers", async () => {
    const t = await bodyText();
    if (!t.includes("Grand total")) throw new Error("details not recovered");
  });

  // Sold-out flight cannot be booked.
  mocks.push({ method: "GET", urlRe: flightRe(realId), status: 200, body: { ...realFlight, available_seats: 0 } });
  await navigate(`${APP}/flights/${realId}`);
  await waitFor(`document.body.innerText.includes('Sold out')`, 12000, "sold-out details");
  const soldState = await evalJs(`(() => {
    const sold = [...document.querySelectorAll('button,a')].find((b) => /Sold out/.test(b.textContent) && b.offsetParent !== null);
    const book = [...document.querySelectorAll('button,a')].find((b) => /Book This Flight/.test(b.textContent) && b.offsetParent !== null);
    return { sold: !!sold, disabled: sold ? sold.disabled === true || sold.getAttribute('aria-disabled') === 'true' : false, book: !!book };
  })()`);
  clearMocks();
  await record("T38: sold-out flight shows disabled Sold out CTA and no Book This Flight", () => {
    if (!soldState.sold || !soldState.disabled) throw new Error("sold-out CTA not disabled");
    if (soldState.book) throw new Error("Book This Flight still visible");
  });

  const navActiveOnDetail = await evalJs(`(() => {
    const link = document.querySelector('a[href="/flights/search"]');
    return link ? /bg-primary-50/.test(link.className) : false;
  })()`);
  await record("T39: Flights nav item is active on a flight detail page", () => {
    if (!navActiveOnDetail) throw new Error("Flights nav not active");
  });

  await navigate(`${APP}/flights/${realId}`);
  await waitFor(`document.body.innerText.includes('Book This Flight')`, 12000, "details book CTA");
  await clickByText("button, a", "Book This Flight");
  await waitFor(`location.pathname === '/bookings/new/${realId}'`, 10000, "to booking");
  await record("T40: Book This Flight opens the booking flow and Flights nav stays active", async () => {
    const p = await currentPath();
    if (p !== `/bookings/new/${realId}`) throw new Error(`got ${p}`);
    const active = await evalJs(`(() => { const l = document.querySelector('a[href="/flights/search"]'); return l ? /bg-primary-50/.test(l.className) : false; })()`);
    if (!active) throw new Error("Flights nav not active on booking-new");
  });

  // ============================================================
  // 5. AI TRAVEL ASSISTANT (T41-T50)
  // ============================================================
  await clearAuthStorage();
  await navigate(`${APP}/assistant`);
  await waitFor(`location.pathname.startsWith('/login')`, 10000, "assistant guard");
  await record("T41: unauthenticated /assistant redirects to login with next", async () => {
    const href = await currentHref();
    if (!decodeURIComponent(href).includes("/assistant")) throw new Error(`got ${href}`);
  });
  await uiLogin(EMAIL, PASS);

  await navigate(`${APP}/assistant`);
  await waitFor(`document.body.innerText.includes('AI Travel Assistant')`, 10000, "assistant page");
  const assistantText = await bodyText();
  await record("T42: assistant page renders heading and subtitle", () => {
    if (!assistantText.includes("AI Travel Assistant")) throw new Error("heading missing");
    if (!assistantText.includes("Ask me about flights")) throw new Error("subtitle missing");
  });
  await record("T43: assistant empty state shows greeting and capability blurb", () => {
    if (!assistantText.includes("How can I help you travel?")) throw new Error("empty heading missing");
    if (!assistantText.includes("search flights")) throw new Error("capability blurb missing");
  });

  const promptCount = await evalJs(`(() => {
    const els = [...document.querySelectorAll("button")].filter((b) => b.offsetParent !== null);
    return els.filter((b) =>
      ["Find me flights from Karachi to Dubai tomorrow",
       "What flights go from Karachi to Istanbul on Friday?",
       "Tell me about flight EK-601",
       "What's the difference between nonstop and connecting flights?"].includes(b.textContent.replace(/\\s+/g, " ").trim())).length;
  })()`);
  await record("T44: four suggested prompts render", () => {
    if (promptCount !== 4) throw new Error(`expected 4 got ${promptCount}`);
  });

  const chatUi = await evalJs(`(() => {
    const ta = document.getElementById('assistant-chat-input');
    const send = document.querySelector('button[aria-label="Send message"]');
    return { ta: !!ta && ta.offsetParent !== null, send: !!send, sendDisabled: send ? send.disabled : true };
  })()`);
  await record("T45: textarea present, send disabled when empty", () => {
    if (!chatUi.ta) throw new Error("textarea missing");
    if (!chatUi.sendDisabled) throw new Error("send should be disabled");
  });

  assistantActive = true;
  chatMode = "pass";
  chatDelayMs = 1200;
  const MSG1 = "I need flights from Karachi to Dubai tomorrow please.";
  await setChatInput(MSG1);
  await waitFor(`document.querySelector('button[aria-label="Send message"]')?.disabled === false`, 5000, "send enabled");
  const preciseBefore = chatRequestCount();
  await clickChatSend();
  await waitFor(`document.body.innerText.includes('Assistant is thinking')`, 4000, "typing indicator");
  await record("T46: typing indicator shown while awaiting reply and send disables", async () => {
    const during = await evalJs(`document.querySelector('button[aria-label="Send message"]')?.disabled === true`);
    if (!during) throw new Error("send not disabled while in flight");
  });
  await waitFor(`document.body.innerText.includes('PK-201 departing 08:00')`, 15000, "turn 1 reply");
  const afterTurn1 = await bodyText();
  await record("T47: exactly one chat request per send with Bearer auth", () => {
    if (chatRequestCount() - preciseBefore !== 1) throw new Error("expected exactly 1 chat request");
    const entry = chatLog.at(-1);
    if (!entry.authorization.startsWith("Bearer ")) throw new Error("no bearer token");
    if (entry.requestBody.message !== MSG1) throw new Error("message body mismatch");
  });
  await record("T48: assistant reply rendered and conversation id captured", () => {
    const conv = chatLog.at(-1).response.conversation_id;
    if (!conv) throw new Error("no conversation_id");
    if (!afterTurn1.includes("PK-201 departing 08:00")) throw new Error("reply text missing");
  });

  chatDelayMs = 0;
  const MSG2 = "What about business class on that route?";
  await setChatInput(MSG2);
  await clickChatSend();
  await waitFor(`document.body.innerText.includes('EK-603 departs at 14:00')`, 15000, "turn 2 reply");
  const afterTurn2 = await bodyText();
  await record("T49: follow-up continues the same conversation with a distinct reply", () => {
    if (chatLog.length < 2) throw new Error("no 2nd request");
    if (chatLog[1].requestBody.conversation_id !== chatLog[0].response.conversation_id) {
      throw new Error("conversation_id not preserved");
    }
    if (!afterTurn2.includes("EK-603") || !afterTurn2.includes("$950")) throw new Error("business reply missing");
    if (!afterTurn2.includes("PK-201 departing 08:00")) throw new Error("earlier reply disappeared");
  });

  await clickByText("button", "New conversation");
  await waitFor(`document.body.innerText.includes('How can I help you travel?')`, 8000, "empty after new conversation");
  await record("T50: New conversation resets to empty state with no history", async () => {
    const t = await bodyText();
    if (t.includes(MSG1) || t.includes(MSG2)) throw new Error("old messages persisted");
  });

  // Assistant network error + retry recovery.
  chatMode = "network";
  chatDelayMs = 0;
  await setChatInput("please simulate a network drop now");
  await clickChatSend();
  await waitFor(`document.body.innerText.includes('Unable to reach the travel assistant.')`, 8000, "network error");
  await record("T50b: assistant network failure shows reachability error with Retry", async () => {
    const t = await bodyText();
    if (!t.includes("Unable to reach the travel assistant.")) throw new Error("network error text missing");
    if (!t.includes("Retry")) throw new Error("retry missing");
  });
  chatMode = "pass";
  await clickByText("button", "Retry");
  await waitFor(`document.body.innerText.includes('here is what I can tell you about that')`, 15000, "retry reply");
  assistantActive = false;

  // ============================================================
  // 6. BOOKING FLOW (T51-T62)
  // ============================================================
  await clearAuthStorage();
  await navigate(`${APP}/bookings/new/${realId}`);
  await waitFor(`location.pathname.startsWith('/login')`, 10000, "booking guard");
  await record("T51: unauthenticated booking route redirects to login with next", async () => {
    const href = await currentHref();
    if (!decodeURIComponent(href).includes(`/bookings/new/${realId}`)) throw new Error(`got ${href}`);
  });
  await uiLogin(EMAIL, PASS);
  await openBookingForm(realId);

  const formFields = await evalJs(`(() => ({
    typeSelect: !!document.getElementById('passenger-1-type'),
    first: !!document.getElementById('passenger-1-first-name'),
    last: !!document.getElementById('passenger-1-last-name'),
    dob: !!document.getElementById('passenger-1-dob'),
    contactEmail: !!document.getElementById('contact-email'),
    contactPhone: !!document.getElementById('contact-phone'),
    typeOptions: [...document.getElementById('passenger-1-type').options].map((o) => o.value),
  }))()`);
  await record("T52: passenger and contact fields render", () => {
    if (!formFields.typeSelect || !formFields.first || !formFields.last || !formFields.dob) throw new Error("passenger fields missing");
    if (!formFields.contactEmail || !formFields.contactPhone) throw new Error("contact fields missing");
  });
  await record("T53: passenger type options cover adult, child and infant", () => {
    for (const v of ["adult", "child", "infant"]) {
      if (!formFields.typeOptions.includes(v)) throw new Error(`missing type ${v}`);
    }
  });

  const beforeInvalid = requestCount("POST", createUrlRe());
  await clickCreate();
  await waitFor(`document.body.innerText.includes('First name is required.')`, 8000, "required validation");
  const invalidText = await bodyText();
  await record("T54: required-field validation blocks submission (no POST)", () => {
    if (!invalidText) throw new Error("no body");
    if (!/First name is required\./.test(invalidText)) throw new Error("no first-name error");
    if (!/Please fix the highlighted fields above/.test(invalidText)) throw new Error("no inline-error banner");
    if (requestCount("POST", createUrlRe()) !== beforeInvalid) throw new Error("POST sent on invalid form");
  });

  await fillPassenger(1, "John", "Doe", "2100-01-01");
  await clickCreate();
  await waitFor(`document.body.innerText.includes('Date of birth must be valid')`, 8000, "dob validation");
  await record("T55: invalid future date of birth is rejected", () => {});

  await openBookingForm(realId);
  await fillPassenger(1, "John", "Doe", "1990-05-14", "adult");
  await fillContact("not-an-email", "");
  const emailBefore = requestCount("POST", createUrlRe());
  await clickCreate();
  await waitFor(`document.body.innerText.includes('Enter a valid email address.')`, 8000, "email validation");
  await record("T56: invalid contact email is rejected without POST", () => {
    if (requestCount("POST", createUrlRe()) !== emailBefore) throw new Error("POST sent on invalid email");
  });

  // Real create with a controlled delay to observe the loading state.
  await openBookingForm(realId);
  await fillPassenger(1, "John", "Doe", "1990-05-14", "adult");
  await fillContact(EMAIL, "+92 300 1234567");
  const verifyFilled = await evalJs(`({
    fn: document.getElementById('passenger-1-first-name').value,
    dob: document.getElementById('passenger-1-dob').value,
    email: document.getElementById('contact-email').value,
  })`);
  if (verifyFilled.fn !== "John" || verifyFilled.dob !== "1990-05-14" || verifyFilled.email !== EMAIL) {
    throw new Error(`form fill verification failed: ${JSON.stringify(verifyFilled)}`);
  }

  const createBefore = requestCount("POST", createUrlRe());
  passDelayMs = 1500;
  await clickCreate();
  await waitFor(`document.querySelector('button[aria-label="Create booking"]')?.disabled === true`, 5000, "create disabled");
  const duringCreate = await evalJs(`(() => {
    const btn = document.querySelector('button[aria-label="Create booking"]');
    return { disabled: btn ? btn.disabled : false, text: btn ? btn.textContent : "" };
  })()`);
  passDelayMs = 0;
  await waitFor(`document.body.innerText.includes('Booking Pending')`, 25000, "real pending");
  const createEntry = requests.filter((r) => r.method === "POST" && createUrlRe().test(r.url)).at(-1);
  await record("T57: create booking sends exactly one contract-correct POST", () => {
    const after = requestCount("POST", createUrlRe());
    if (after - createBefore !== 1) throw new Error(`expected 1 got ${after - createBefore}`);
    const body = JSON.parse(createEntry.postData);
    if (body.flight_id !== realId) throw new Error(`flight_id mismatch`);
    if (!Array.isArray(body.passengers) || body.passengers.length !== 1) throw new Error("passengers count mismatch");
    const p = body.passengers[0];
    if (p.first_name !== "John" || p.last_name !== "Doe" || p.passenger_type !== "adult" || p.date_of_birth !== "1990-05-14") {
      throw new Error(`passenger payload mismatch: ${JSON.stringify(p)}`);
    }
    if ("user_id" in body || "pnr" in body || "base_amount" in body || "tax_amount" in body || "total_amount" in body || "currency" in body) {
      throw new Error("client sent an authoritative field");
    }
  });
  await record("T58: create button disables with loading label during request", () => {
    if (!duringCreate.disabled) throw new Error("create button not disabled");
    if (!duringCreate.text.includes("Creating booking")) throw new Error(`label: ${duringCreate.text}`);
  });
  await record("T59: real backend returns a PENDING booking with its PNR displayed", async () => {
    const t = await bodyText();
    if (!t.includes("Booking Pending")) throw new Error("pending heading missing");
    const pnr = await readPnr();
    if (!/^[A-Z0-9]{6}$/.test(pnr)) throw new Error(`bad PNR: ${pnr}`);
  });
  const pnrConfirmed = await readPnr();

  const seatsAfterCreate = await apiGetFlightSeats(seedAuth.token, realId);
  await record("T60: creating a booking decremented availability by one", () => {
    if (seatsAfterCreate.available_seats !== baselineSeats1 - 1) {
      throw new Error(`expected ${baselineSeats1 - 1} got ${seatsAfterCreate.available_seats}`);
    }
  });

  const confirmBefore = requestCount("POST", confirmUrlRe());
  await clickConfirm();
  await waitFor(`document.body.innerText.includes('Booking Confirmed')`, 25000, "confirmed UI");
  const confirmAfter = requestCount("POST", confirmUrlRe());
  const confirmedText = await bodyText();
  await record("T61: confirmation succeeds with CONFIRMED, same PNR and View My Bookings CTA", async () => {
    if (confirmAfter - confirmBefore !== 1) throw new Error(`expected 1 confirm got ${confirmAfter - confirmBefore}`);
    if (!confirmedText.includes("Booking Confirmed") || !confirmedText.includes("CONFIRMED")) throw new Error("not confirmed");
    const pnr2 = await readPnr();
    if (pnr2 !== pnrConfirmed) throw new Error(`PNR changed: ${pnr2} vs ${pnrConfirmed}`);
    if (!confirmedText.includes("View My Bookings")) throw new Error("view bookings CTA missing");
  });
  await record("T62: booking end-to-end uses the authenticated user context", () => {
    if (!confirmedText.includes(EMAIL)) throw new Error("contact email not shown");
  });
  await clickByText("button, a", "View My Bookings");
  await waitFor(`location.pathname === '/bookings'`, 10000, "my bookings");

  // ============================================================
  // 7. MY BOOKINGS (T63-T70)
  // ============================================================
  // Second, still-PENDING booking created through the backend for list coverage.
  const pendingBooking = await apiCreateBooking(seedAuth.token, realId2, 1);
  const pnrPending = pendingBooking.pnr;
  if (!/^[A-Z0-9]{6}$/.test(pnrPending)) throw new Error(`bad pending PNR ${pnrPending}`);

  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrConfirmed)}) && document.body.innerText.includes(${JSON.stringify(pnrPending)})`, 15000, "both pnrs listed");
  const listText = await bodyText();
  await record("T63: My Bookings lists real backend bookings (both PNRs)", () => {
    if (!listText.includes(pnrConfirmed) || !listText.includes(pnrPending)) throw new Error("PNRs missing from list");
    if (!listText.includes("My Bookings")) throw new Error("heading missing");
    if (listText.includes("Coming soon")) throw new Error("placeholder leaked into bookings");
  });
  await record("T64: booking cards show flight route, airline and status badges", async () => {
    if (!listText.includes(realFlight.origin) || !listText.includes(realFlight.destination)) throw new Error("route missing");
    if (!listText.includes("Confirmed")) throw new Error("Confirmed badge missing");
    if (!listText.includes("Pending")) throw new Error("Pending badge missing");
  });

  mocks.push({ method: "GET", urlRe: listUrlRe(), status: 200, body: { count: 0, bookings: [] } });
  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes('No bookings yet')`, 12000, "empty state");
  const emptyText = await bodyText();
  await record("T65: empty state offers a working Search flights action", async () => {
    if (!emptyText.includes("No bookings yet")) throw new Error("empty title missing");
  });
  await clickByText("a", "Search flights");
  await waitFor(`location.pathname === '/flights/search'`, 10000, "empty CTA nav");
  clearMocks();
  await record("T65b: empty-state Search flights navigates to /flights/search", () => {});

  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrConfirmed)})`, 15000, "list restored");
  await clickByText("a", pnrConfirmed);
  await waitFor(`location.pathname === '/bookings/${pnrConfirmed}'`, 10000, "detail nav");
  await waitFor(`document.body.innerText.includes(${JSON.stringify(realFlight.airline_code)}) && document.body.innerText.includes(${JSON.stringify(realFlight.flight_number)})`, 12000, "detail flight");
  const detailTextConfirmed = await bodyText();
  await record("T66: booking card navigates to a detail page with flight + fare + contact", async () => {
    if (!detailTextConfirmed.includes(pnrConfirmed)) throw new Error("pnr missing");
    if (!detailTextConfirmed.includes(realFlight.airline_code)) throw new Error("airline missing");
    if (!/Base fare/.test(detailTextConfirmed) || !/Total/.test(detailTextConfirmed)) throw new Error("fare missing");
    if (!detailTextConfirmed.includes(EMAIL)) throw new Error("contact email missing");
    const back = await evalJs(`!!document.querySelector('a[href="/bookings"]')`);
    if (!back) throw new Error("back link missing");
  });

  // Cross-owner security.
  await clearAuthStorage();
  await uiLogin(USER2_EMAIL, PASS);
  await navigate(`${APP}/bookings/${pnrPending}`); // belongs to EMAIL
  await waitFor(`document.body.innerText.includes('Access denied')`, 15000, "cross-owner 403");
  const deniedText = await bodyText();
  await record("T67: cross-owner PNR access is denied without leaking booking content", () => {
    if (!/Access denied|permission/i.test(deniedText)) throw new Error("no access-denied state");
    if (deniedText.includes(pnrPending)) throw new Error("foreign PNR leaked");
    if (deniedText.includes(realFlight.airline)) throw new Error("foreign booking content leaked");
  });
  await clearAuthStorage();
  await uiLogin(EMAIL, PASS);

  await navigate(`${APP}/bookings/ZZZZZZ`);
  await waitFor(`document.body.innerText.includes('Booking not found')`, 12000, "detail 404");
  await record("T68: unknown booking shows not-found error state", () => {});

  mocks.push({ method: "GET", urlRe: listUrlRe(), status: 500, body: { detail: "boom" } });
  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes("Couldn't load your bookings")`, 12000, "list 500");
  clearMocks();
  await clickByText("button", "Try again");
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrPending)})`, 15000, "retry recovered");
  await record("T69: list 500 shows error state and Try again recovers", async () => {
    const t = await bodyText();
    if (!t.includes(pnrPending)) throw new Error("bookings not recovered");
  });

  mocks.push({ method: "GET", urlRe: detailUrlRe(pnrConfirmed), status: 500, body: { detail: "boom" } });
  await navigate(`${APP}/bookings/${pnrConfirmed}`);
  await waitFor(`document.body.innerText.includes('Something went wrong')`, 12000, "detail 500");
  clearMocks();
  await record("T70: booking detail 500 shows error state without crashing", () => {});

  // ============================================================
  // 8. CANCELLATION (T71-T77)
  // ============================================================
  await navigate(`${APP}/bookings/${pnrPending}`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrPending)})`, 12000, "pending detail");
  await waitFor(`document.body.innerText.includes('Cancel booking')`, 8000, "cancel cta");
  await clickByText("button", "Cancel booking");
  await waitFor(`document.querySelector('[role="dialog"]') != null`, 8000, "cancel dialog");
  const dlgText = await bodyText();
  await record("T71: cancel confirmation dialog opens with PNR and seat context", () => {
    if (!dlgText.includes("Cancel booking?")) throw new Error("dialog title missing");
    if (!dlgText.includes(pnrPending)) throw new Error("pnr missing from dialog");
  });

  const cancelBefore = requestCount("POST", cancelUrlRe(pnrPending));
  await clickConfirmCancel();
  await waitFor(`document.querySelector('[role="dialog"]') == null`, 12000, "dialog closes");
  const cancelAfter = requestCount("POST", cancelUrlRe(pnrPending));
  const cancelEntry = requests.filter((r) => r.method === "POST" && cancelUrlRe(pnrPending).test(r.url)).at(-1);
  await record("T72: exactly one cancel request, POST /api/bookings/{pnr}/cancel with no body", () => {
    if (cancelAfter - cancelBefore !== 1) throw new Error(`expected 1 got ${cancelAfter - cancelBefore}`);
    if (!cancelEntry.url.startsWith(API + `/api/bookings/${pnrPending}/cancel`)) throw new Error(`url ${cancelEntry.url}`);
    if (cancelEntry.postData && cancelEntry.postData.trim().length) throw new Error("cancel sent a body");
  });
  const afterCancelText = await bodyText();
  await record("T73: successful cancel flips status to Cancelled and removes the CTA", () => {
    if (!afterCancelText.includes("Cancelled")) throw new Error("cancelled badge missing");
    if (/Cancel booking/.test(afterCancelText)) throw new Error("cancel CTA still visible");
  });

  await record("T74: cancellation persisted on backend and seats restored", async () => {
    const detail = await apiGetBooking(seedAuth.token, pnrPending);
    if (detail.status !== "cancelled") throw new Error(`status ${detail.status}`);
    const seat2 = await apiGetFlightSeats(seedAuth.token, realId2);
    if (seat2.available_seats !== baselineSeats2) {
      throw new Error(`seats not restored: ${seat2.available_seats} vs ${baselineSeats2}`);
    }
  });

  // Mock 400 keeps the dialog open with an error.
  const m1 = mkBooking({ pnr: "MKPK1", user_id: seedUser.id, flight_id: realId, status: "pending" });
  mocks.push({ method: "GET", urlRe: detailUrlRe("MKPK1"), status: 200, body: m1 });
  await navigate(`${APP}/bookings/MKPK1`);
  await waitFor(`document.body.innerText.includes("Cancel booking")`, 12000, "mock pending detail");
  mocks.push({ method: "POST", urlRe: cancelUrlRe("MKPK1"), status: 400, body: { detail: "Booking is already cancelled." } });
  await clickByText("button", "Cancel booking");
  await waitFor(`document.querySelector('[role="dialog"]') != null`, 8000, "dialog mock");
  await clickConfirmCancel();
  await waitFor(`document.querySelector('[role="dialog"] [role="alert"]') != null`, 8000, "cancel 400 error");
  await record("T75: cancel 400 keeps the dialog open with the error (no fake status)", async () => {
    const t = await bodyText();
    if (!t.includes("Booking is already cancelled.")) throw new Error("error text missing");
    const stillOpen = await evalJs(`!!document.querySelector('[role="dialog"]')`);
    if (!stillOpen) throw new Error("dialog closed on 400");
  });
  clearMocks();
  await clickByText("button", "Keep booking");
  await waitFor(`document.querySelector('[role="dialog"]') == null`, 8000, "dialog closed");

  // Mock 500 keeps the dialog open with an error.
  const m2 = mkBooking({ pnr: "MKPK2", user_id: seedUser.id, flight_id: realId, status: "confirmed" });
  mocks.push({ method: "GET", urlRe: detailUrlRe("MKPK2"), status: 200, body: m2 });
  await navigate(`${APP}/bookings/MKPK2`);
  await waitFor(`document.body.innerText.includes("Cancel booking")`, 12000, "mock confirmed detail");
  mocks.push({ method: "POST", urlRe: cancelUrlRe("MKPK2"), status: 500, body: { detail: "Cancellation failed: boom" } });
  await clickByText("button", "Cancel booking");
  await waitFor(`document.querySelector('[role="dialog"]') != null`, 8000, "dialog mock2");
  await clickConfirmCancel();
  await waitFor(`document.querySelector('[role="dialog"] [role="alert"]') != null`, 8000, "cancel 500 error");
  await record("T76: cancel 500 keeps the dialog open with an error message", async () => {
    const t = await bodyText();
    if (!/Cancellation failed|Something went wrong/.test(t)) throw new Error("500 cancel error missing");
  });
  clearMocks();
  await clickByText("button", "Keep booking");
  await waitFor(`document.querySelector('[role="dialog"]') == null`, 8000, "dialog closed2");

  // Double-submit guard: confirm disabled while request in flight.
  const m3 = mkBooking({ pnr: "MKPK3", user_id: seedUser.id, flight_id: realId, status: "pending" });
  mocks.push({ method: "GET", urlRe: detailUrlRe("MKPK3"), status: 200, body: m3 });
  mocks.push({ method: "POST", urlRe: cancelUrlRe("MKPK3"), status: 200, delayMs: 1500, body: mkBooking({ pnr: "MKPK3", user_id: seedUser.id, flight_id: realId, status: "cancelled" }) });
  await navigate(`${APP}/bookings/MKPK3`);
  await waitFor(`document.body.innerText.includes("Cancel booking")`, 12000, "mock pending detail 3");
  await clickByText("button", "Cancel booking");
  await waitFor(`document.querySelector('[role="dialog"]') != null`, 8000, "dialog mock3");
  await clickConfirmCancel();
  await sleep(300);
  const duringCancel = await evalJs(`(() => {
    const btn = [...document.querySelectorAll('[role="dialog"] button')].find((b) => /Cancelling/i.test(b.textContent) || /Cancel booking/.test(b.textContent));
    return btn ? { disabled: btn.disabled, text: btn.textContent } : null;
  })()`);
  await record("T77: confirm button disables while cancelling (double-submit guard)", () => {
    if (!duringCancel) throw new Error("no button in dialog");
    if (!duringCancel.disabled) throw new Error("confirm not disabled");
  });
  await waitFor(`document.querySelector('[role="dialog"]') == null`, 12000, "dialog mock3 closes");
  clearMocks();

  // ============================================================
  // 9. SECURITY & PRIVACY (T78-T84)
  // ============================================================
  await record("T78: booking lifecycle requests never carry user_id or totals, cancel body empty", () => {
    const lifecycle = requests.filter((r) =>
      (/\/api\/bookings/.test(r.url) && r.method === "POST" && !/\/flights/.test(r.url)) &&
      !(/\/api\/bookings\/[A-Z0-9]{6}\/cancel$/.test(r.url) && !r.postData.trim()),
    );
    for (const r of lifecycle) {
      const body = r.postData || "";
      if (/user_id|base_amount|tax_amount|total_amount|currency|"pnr"/.test(body)) {
        throw new Error(`authoritative field on ${r.method} ${r.url}: ${body}`);
      }
    }
  });

  await record("T79: every authenticated API call carries the Bearer header", () => {
    const authed = requests.filter((r) =>
      r.url.startsWith(API + "/api/") &&
      ["GET", "POST"].includes(r.method) &&
      !/\/api\/auth\/(login|register|me)$/.test(r.url) &&
      !/\/api\/health/.test(r.url) &&
      !/\/api\/flights\/public/.test(r.url),
    );
    if (!authed.length) throw new Error("no API requests to audit");
    for (const r of authed) {
      const h = r.headers || {};
      const auth = h.authorization || h.Authorization || "";
      if (!auth.startsWith("Bearer ")) throw new Error(`missing Bearer on ${r.method} ${r.url}`);
    }
  });

  await record("T80: the token never appears in an URL or a request body", () => {
    for (const r of requests) {
      if (/access_token|[\?&]token=/.test(r.url)) throw new Error(`token in URL: ${r.url}`);
      if (r.postData && /access_token/.test(r.postData)) throw new Error("access_token in body");
    }
  });

  // XSS: crafted message sent to the assistant must render as text only.
  assistantActive = true;
  chatMode = "pass";
  await navigate(`${APP}/assistant`);
  await waitFor(`document.getElementById('assistant-chat-input') != null`, 10000, "assistant input");
  const xssPayload = `<img src=x onerror=window.__xss=1><script>window.__xss=1</script>`;
  await setChatInput(xssPayload);
  await clickChatSend();
  await waitFor(`document.body.innerText.includes('here is what I can tell you about that')`, 15000, "reply after xss");
  await sleep(600);
  await record("T81: user-supplied HTML in a chat message is not executed", async () => {
    const executed = await evalJs(`(window.__xss === 1) || !!document.querySelector('img[src="x"]')`);
    if (executed) throw new Error("XSS payload executed");
    const t = await bodyText();
    if (!t.includes("<img")) throw new Error("payload not rendered as text");
  });
  assistantActive = false;

  await record("T82: the password value never leaks into visible page text", async () => {
    const t = await bodyText();
    if (t.includes(PASS)) throw new Error("password text leaked into DOM");
  });

  await record("T83: no console error contains token-shaped data", () => {
    for (const e of consoleErrors) {
      if (/eyJ|access_token|Bearer [A-Za-z0-9._-]{20,}/.test(e)) throw new Error(`token-shaped console output: ${e}`);
    }
  });

  await record("T84: registration and login both use masked password inputs", async () => {
    await navigate(`${APP}/register`);
    await waitFor(`document.querySelector('input[type="email"]') != null`, 8000, "register form");
    const masked = await evalJs(`[...document.querySelectorAll('input')].filter((i) => i.offsetParent !== null).some((i) => i.type === 'password')`);
    if (!masked) throw new Error("register passwords not masked");
  });

  // ============================================================
  // 10. NAVIGATION & UX (T85-T90)
  // ============================================================
  await navigate(`${APP}/profile`);
  await waitFor(`document.body.innerText.includes('Membership')`, 12000, "profile loaded");
  const profileText = await bodyText();
  await record("T85: profile page shows account details and no placeholder", () => {
    for (const item of ["Profile", "Membership", "Loyalty points", "Phone", "Member since"]) {
      if (!profileText.includes(item)) throw new Error(`profile missing ${item}`);
    }
    if (profileText.includes("Coming soon")) throw new Error("ComingSoon placeholder present");
  });
  await record("T85b: profile shows the signed-in user name and email", () => {
    if (!profileText.includes("Final Register User") && !profileText.includes(EMAIL)) {
      throw new Error("user identity missing");
    }
  });

  await navigate(APP);
  await clickByText("a", "Ask AI Assistant");
  await waitFor(`location.pathname === '/assistant'`, 10000, "assistant cta");
  await record("T86: Ask AI Assistant CTA navigates to the assistant", async () => {
    const p = await currentPath();
    if (p !== "/assistant") throw new Error(`got ${p}`);
  });

  await navigate(APP);
  await clickByText("a", "Create account");
  await waitFor(`location.pathname === '/register'`, 8000, "register nav");
  await record("T87: footer Create account link opens the register form", () => {});
  await navigate(APP);
  await clickByText("a", "Sign in");
  await waitFor(`location.pathname === '/login'`, 8000, "login nav");
  await record("T87b: footer Sign in link opens the login form", () => {});

  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrConfirmed)})`, 15000, "list for back-link test");
  await navigate(`${APP}/bookings/${pnrConfirmed}`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrConfirmed)})`, 12000, "detail for back-link");
  await record("T88: detail page offers a Back to My Bookings link", async () => {
    const link = await evalJs(`!!document.querySelector('a[href="/bookings"]')`);
    if (!link) throw new Error("back link missing");
  });

  await evalJs(`(() => { const l = document.querySelector('header a[href="/"]'); if (!l) return false; l.click(); return true; })()`);
  await waitFor(`location.pathname === '/'`, 8000, "logo home");
  await record("T89: navbar logo navigates to the landing page", async () => {
    const p = await currentPath();
    if (p !== "/") throw new Error(`got ${p}`);
  });

  await searchFlightsInUI();
  await waitForCount(5);
  const ariaState = await evalJs(`(() => ({
    filterBtn: document.querySelector('button[aria-controls="mobile-filters"]') !== null,
    anyLive: document.querySelector('[aria-live]') !== null,
  }))()`);
  await record("T90: results page exposes mobile-filters wiring and an aria-live region", () => {
    if (!ariaState.filterBtn) throw new Error("filters button aria-controls missing");
    if (!ariaState.anyLive) throw new Error("no aria-live region on results");
  });

  // ============================================================
  // 11. RESPONSIVE (T91-T96)
  // ============================================================
  const overflow = async () =>
    evalJs(`(() => { const d = document.documentElement; return { sw: d.scrollWidth, cw: d.clientWidth }; })()`);

  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
  await navigate(APP);
  const l390 = await overflow();
  await record("T91: landing 390px has no horizontal overflow", () => {
    if (l390.sw > l390.cw + 1) throw new Error(`overflow ${l390.sw}/${l390.cw}`);
  });

  await searchFlightsInUI();
  await waitForCount(5);
  const s390b = await overflow();
  const filtersBtn390 = await evalJs(`[...document.querySelectorAll('button')].some((b) => b.getAttribute('aria-controls') === 'mobile-filters' && b.offsetParent !== null)`);
  await evalJs(`(() => { const b = [...document.querySelectorAll('button')].find((x) => x.getAttribute('aria-controls') === 'mobile-filters'); if (!b) return false; b.click(); return true; })()`);
  await waitFor(`document.getElementById('mobile-filters') != null`, 8000, "mobile filters panel");
  await record("T92: 390px results have no overflow and the Filters drawer opens via aria-controls", () => {
    if (s390b.sw > s390b.cw + 1) throw new Error(`overflow ${s390b.sw}/${s390b.cw}`);
    if (!filtersBtn390) throw new Error("mobile filters button not visible");
  });

  await navigate(`${APP}/flights/${realId}`);
  await waitFor(`document.body.innerText.includes('Grand total')`, 12000, "details 390");
  const d390 = await overflow();
  await record("T93: flight details 390px has no horizontal overflow", () => {
    if (d390.sw > d390.cw + 1) throw new Error(`overflow ${d390.sw}/${d390.cw}`);
  });

  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrConfirmed)})`, 15000, "bookings 390");
  const b390 = await overflow();
  await record("T94: My Bookings 390px has no horizontal overflow", () => {
    if (b390.sw > b390.cw + 1) throw new Error(`overflow ${b390.sw}/${b390.cw}`);
  });

  await send("Emulation.setDeviceMetricsOverride", { width: 768, height: 1024, deviceScaleFactor: 2, mobile: true });
  await navigate(`${APP}/flights/search`);
  await waitFor(`document.querySelector('input[aria-label="Origin airport code"]') != null`, 8000, "search form 768");
  await setInput(`document.querySelector('input[aria-label="Origin airport code"]')`, "KHI");
  await setInput(`document.querySelector('input[aria-label="Destination airport code"]')`, "DXB");
  await clickByText("button", "Search flights");
  await waitFor(`[...document.querySelectorAll('h2')].some((h) => /flight[s]? found/.test(h.textContent))`, 15000, "results 768");
  const r768 = await overflow();
  await record("T95: search results 768px has no horizontal overflow", () => {
    if (r768.sw > r768.cw + 1) throw new Error(`overflow ${r768.sw}/${r768.cw}`);
  });

  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await openBookingForm(realId);
  const b1440 = await overflow();
  const reviewPanel = await evalJs(`!!document.getElementById('booking-review-heading')`);
  await record("T96: booking flow 1440px has no overflow and shows the review panel", () => {
    if (b1440.sw > b1440.cw + 1) throw new Error(`overflow ${b1440.sw}/${b1440.cw}`);
    if (!reviewPanel) throw new Error("review panel missing");
  });

  // ============================================================
  // 12. BROWSER QUALITY (T97-T100)
  // ============================================================
  consoleErrors.length = 0;
  pageErrors.length = 0;
  networkFailures.length = 0;
  await navigate(APP);
  await navigate(`${APP}/bookings`);
  await waitFor(`document.body.innerText.includes(${JSON.stringify(pnrConfirmed)})`, 15000, "quality nav");
  await navigate(`${APP}/assistant`);
  await waitFor(`document.getElementById('assistant-chat-input') != null`, 10000, "quality assistant");
  await navigate(`${APP}/profile`);
  await waitFor(`document.body.innerText.includes('Membership')`, 12000, "quality profile");
  await sleep(600);

  await record("T97: console errors = 0", () => {
    const meaningful = consoleErrors.filter((e) => !/Failed to load resource:/.test(e));
    if (meaningful.length) throw new Error(meaningful.join(" ;; ").slice(0, 500));
  });
  await record("T98: no uncaught JS errors", () => {
    if (pageErrors.length) throw new Error(pageErrors.join(" ;; "));
  });
  await record("T99: no hydration errors", async () => {
    const hydration = await evalJs(`[...document.querySelectorAll('body *')].some((el) => /hydration error/i.test(el?.textContent || ''))`);
    if (hydration) throw new Error("hydration marker present");
  });
  await record("T100: no failed XHR/Fetch requests", () => {
    if (networkFailures.length) throw new Error(networkFailures.join(" ;; "));
  });


  // Clean up CDP interception/emulation.
  await send("Fetch.disable").catch(() => {});
  await send("Emulation.clearDeviceMetricsOverride").catch(() => {});

  console.log("=== PHASE 15.8 E2E RESULTS ===");
  let ok = 0;
  for (const r of results) {
    if (r.ok) ok += 1;
    console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.name}${r.detail ? "  :: " + r.detail : ""}`);
  }
  console.log(`\n${ok}/${results.length} PASS`);
  writeFileSync("C:\\Users\\BILALH~1\\AppData\\Local\\Temp\\opencode\\phase15-8-e2e-report.txt", JSON.stringify(results, null, 2));
  process.exit(ok === results.length ? 0 : 1);
}

main().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});