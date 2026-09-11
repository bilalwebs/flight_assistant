"""
Phase 14 — HTTP API Endpoint Tests.

End-to-end tests using FastAPI TestClient. Verifies real HTTP request/response
cycle, authentication enforcement, ownership isolation, and error handling.

Mocks Stripe and LLM calls to avoid external dependencies.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Ensure backend root is importable when run from tests/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from agents import set_tracing_disabled
set_tracing_disabled(True)

# Import app and DB helpers
from main import app
from database.database import AsyncSessionLocal, init_db
from models.flight import Flight, CabinClass


client = TestClient(app)


def _unique_email():
    return f"http_{uuid.uuid4().hex[:8]}@example.com"


async def _create_flight() -> str:
    """Insert a bookable flight directly and return its ID."""
    flight_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        flight = Flight(
            id=flight_id,
            flight_number=f"HT-{uuid.uuid4().hex[:4].upper()}",
            airline="HTTP Test Air",
            airline_code="HT",
            origin="KHI",
            destination="DXB",
            origin_city="Karachi",
            destination_city="Dubai",
            origin_country="Pakistan",
            destination_country="UAE",
            departure_time=datetime.now(timezone.utc) + timedelta(days=2),
            arrival_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
            duration_minutes=120,
            stops=0,
            cabin_class=CabinClass.ECONOMY,
            base_price=150.0,
            tax_percent=15.0,
            total_seats=180,
            available_seats=180,
        )
        session.add(flight)
        await session.commit()
    return flight_id


def _register_and_login(email=None, password="SecurePass123", name="HTTP User"):
    """Register + login, return (token, user_dict)."""
    email = email or _unique_email()
    reg = client.post("/api/auth/register", json={
        "email": email, "password": password, "name": name,
    })
    assert reg.status_code == 201, f"register failed: {reg.text}"
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, f"login failed: {login.text}"
    body = login.json()
    return body["access_token"], body["user"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_register_returns_no_password_hash():
    email = _unique_email()
    r = client.post("/api/auth/register", json={
        "email": email, "password": "SecurePass123", "name": "Alice",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert body["email"] == email
    print("[PASS] register: 201, no password hash exposed")


def test_register_duplicate_returns_409():
    email = _unique_email()
    payload = {"email": email, "password": "SecurePass123", "name": "Bob"}
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409, r2.text
    print("[PASS] register duplicate: 409 Conflict")


def test_register_invalid_data_returns_422():
    r = client.post("/api/auth/register", json={
        "email": "not-an-email", "password": "short", "name": "",
    })
    assert r.status_code == 422, r.text
    print("[PASS] register invalid data: 422")


def test_login_success_returns_token():
    token, user = _register_and_login()
    assert token and len(token) > 10
    assert user["id"]
    print("[PASS] login: returns bearer token + user")


def test_login_wrong_password_returns_401():
    email = _unique_email()
    client.post("/api/auth/register", json={
        "email": email, "password": "SecurePass123", "name": "Carol",
    })
    r = client.post("/api/auth/login", json={"email": email, "password": "WrongPass999"})
    assert r.status_code == 401, r.text
    print("[PASS] login wrong password: 401")


def test_me_requires_auth():
    r = client.get("/api/auth/me")
    assert r.status_code == 401, r.text
    print("[PASS] /me without token: 401")


def test_me_returns_safe_user():
    token, user = _register_and_login()
    r = client.get("/api/auth/me", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == user["id"]
    assert "password_hash" not in body
    print("[PASS] /me with token: safe user data")


def test_invalid_token_rejected():
    r = client.get("/api/auth/me", headers=_auth("garbage.token.value"))
    assert r.status_code == 401, r.text
    print("[PASS] invalid token: 401")


# ---------------------------------------------------------------------------
# Flights (protected)
# ---------------------------------------------------------------------------

def test_flight_endpoints_require_auth():
    r = client.post("/api/flights/search", json={
        "origin": "KHI", "destination": "DXB",
        "date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    })
    assert r.status_code == 401, r.text
    print("[PASS] flight search without token: 401")


def test_flight_details_404(sync_flight_id):
    token, _ = _register_and_login()
    r = client.get(f"/api/flights/{uuid.uuid4()}", headers=_auth(token))
    assert r.status_code == 404, r.text
    print("[PASS] flight details missing: 404")


def test_flight_search_and_price(sync_flight_id):
    token, _ = _register_and_login()
    # search
    r = client.post("/api/flights/search", headers=_auth(token), json={
        "origin": "KHI", "destination": "DXB",
        "date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "cabin_class": "economy",
    })
    assert r.status_code == 200, r.text
    # price calc
    r2 = client.post(
        f"/api/flights/price?flight_id={sync_flight_id}&passenger_count=2",
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["grand_total"] == body["total_per_person"] * 2
    print("[PASS] flight search + price calculation")


def test_seat_availability(sync_flight_id):
    token, _ = _register_and_login()
    r = client.get(f"/api/flights/{sync_flight_id}/seats", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_seats"] == 180
    print("[PASS] seat availability")


# ---------------------------------------------------------------------------
# Bookings (protected + ownership)
# ---------------------------------------------------------------------------

def test_booking_requires_auth():
    r = client.post("/api/bookings", json={"flight_id": "x", "passengers": []})
    assert r.status_code == 401, r.text
    print("[PASS] create booking without token: 401")


def _make_booking(token, flight_id):
    return client.post("/api/bookings", headers=_auth(token), json={
        "flight_id": flight_id,
        "passengers": [{
            "first_name": "John", "last_name": "Doe",
            "passenger_type": "adult", "date_of_birth": "1990-01-01",
        }],
        "cabin_class": "economy",
    })


def test_booking_create_and_get(sync_flight_id):
    token, _ = _register_and_login()
    r = _make_booking(token, sync_flight_id)
    assert r.status_code == 201, r.text
    pnr = r.json()["pnr"]

    r2 = client.get(f"/api/bookings/{pnr}", headers=_auth(token))
    assert r2.status_code == 200, r2.text
    assert r2.json()["pnr"] == pnr
    print("[PASS] booking create + retrieve")


def test_booking_ownership_isolation(sync_flight_id):
    # User A creates a booking
    token_a, _ = _register_and_login()
    r = _make_booking(token_a, sync_flight_id)
    assert r.status_code == 201, r.text
    pnr = r.json()["pnr"]

    # User B attempts to access it
    token_b, _ = _register_and_login()
    r2 = client.get(f"/api/bookings/{pnr}", headers=_auth(token_b))
    assert r2.status_code == 403, r2.text
    print("[PASS] booking ownership isolation: user B gets 403")


def test_booking_list_only_own(sync_flight_id):
    token_a, _ = _register_and_login()
    _make_booking(token_a, sync_flight_id)
    _make_booking(token_a, sync_flight_id)

    token_b, _ = _register_and_login()
    r = client.get("/api/bookings", headers=_auth(token_b))
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 0  # B has no bookings
    print("[PASS] booking list scoped to authenticated user")


# ---------------------------------------------------------------------------
# Payments (protected + ownership + authoritative price)
# ---------------------------------------------------------------------------

def test_payment_requires_auth():
    r = client.post("/api/payments/checkout", json={"booking_id": "x"})
    assert r.status_code == 401, r.text
    print("[PASS] payment checkout without token: 401")


@patch("services.payment_service.stripe.checkout.Session.create")
def test_payment_checkout_uses_db_price(mock_create, sync_flight_id):
    mock_create.return_value = MagicMock(
        id="cs_http_test", url="https://checkout.stripe.com/pay/cs_http_test"
    )
    token, _ = _register_and_login()
    booking = _make_booking(token, sync_flight_id)
    assert booking.status_code == 201, booking.text
    booking_body = booking.json()
    booking_id = booking_body["id"]
    db_total = booking_body["total_amount"]

    # Attempt to manipulate price via extra field — should be ignored
    r = client.post("/api/payments/checkout", headers=_auth(token), json={
        "booking_id": booking_id,
        "amount": 1,  # malicious low price — must be ignored
    })
    assert r.status_code == 200, r.text

    # Verify Stripe was called with authoritative DB amount (cents)
    _, kwargs = mock_create.call_args
    line_item = kwargs["line_items"][0]
    charged_cents = line_item["price_data"]["unit_amount"]
    assert charged_cents == int(round(db_total * 100)), (
        f"expected {int(round(db_total*100))} cents, got {charged_cents}"
    )
    print("[PASS] payment uses authoritative DB price (client amount ignored)")


@patch("services.payment_service.stripe.checkout.Session.create")
def test_payment_ownership_enforced(mock_create, sync_flight_id):
    mock_create.return_value = MagicMock(
        id="cs_owner_test", url="https://checkout.stripe.com/pay/cs_owner_test"
    )
    token_a, _ = _register_and_login()
    booking = _make_booking(token_a, sync_flight_id)
    booking_id = booking.json()["id"]

    token_b, _ = _register_and_login()
    r = client.post("/api/payments/checkout", headers=_auth(token_b), json={
        "booking_id": booking_id,
    })
    assert r.status_code == 403, r.text
    print("[PASS] payment ownership enforced: user B gets 403")


# ---------------------------------------------------------------------------
# Webhook signature enforcement (must NOT have JWT, must verify signature)
# ---------------------------------------------------------------------------

def test_webhook_rejects_bad_signature():
    r = client.post(
        "/api/payments/webhook",
        headers={"stripe-signature": "t=123,v1=badsig"},
        content=b'{"id":"evt_test","type":"charge.succeeded"}',
    )
    # Signature verification must fail with 400 (not 401 — no JWT here)
    assert r.status_code == 400, r.text
    print("[PASS] webhook rejects bad signature: 400 (no JWT required)")


# ---------------------------------------------------------------------------
# Assistant chat (LLM mocked to avoid external dependency)
# ---------------------------------------------------------------------------

def test_assistant_requires_auth():
    r = client.post("/api/assistant/chat", json={"message": "hello"})
    assert r.status_code == 401, r.text
    print("[PASS] assistant chat without token: 401")


@patch("sessions.session_manager.Runner.run")
def test_assistant_chat_with_context(mock_run):
    """Authenticated assistant request returns response and preserves context prefs."""
    mock_run.return_value = MagicMock(final_output="Hello! How can I help you book a flight?")
    token, _ = _register_and_login()
    r = client.post("/api/assistant/chat", headers=_auth(token), json={
        "message": "I want a business cabin to Dubai",
        "origin_preference": "KHI",
        "destination_preference": "DXB",
        "cabin_preference": "business",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert len(body["conversation_id"]) > 0
    assert body["message"]

    # Context preferences from request preserved AND user identity from token
    _, kwargs = mock_run.call_args
    ctx = kwargs["context"]
    assert ctx.origin_preference == "KHI"
    assert ctx.destination_preference == "DXB"
    assert ctx.cabin_preference == "business"
    assert ctx.preferred_cabin_class == "business"
    print("[PASS] assistant chat: returns response, preserves request context")


@patch("sessions.session_manager.Runner.run")
def test_assistant_user_from_token_not_request(mock_run):
    """Client cannot impersonate another user via request body."""
    mock_run.return_value = MagicMock(final_output="ok")
    token, _ = _register_and_login()
    r = client.post("/api/assistant/chat", headers=_auth(token), json={
        "message": "hi", "user_id": "attacker-controlled-id",
    })
    assert r.status_code == 200, r.text
    _, kwargs = mock_run.call_args
    ctx = kwargs["context"]
    # context.user_id must come from the token's user, never the request field
    auth_user = client.get("/api/auth/me", headers=_auth(token)).json()
    assert ctx.user_id == auth_user["id"]
    assert ctx.user_id != "attacker-controlled-id"
    print("[PASS] assistant chat: user_id taken from token, request cannot spoof")


@patch("sessions.session_manager.Runner.run")
def test_assistant_conversation_isolation(mock_run):
    """Different conversation_id for same user hit different session ids."""
    mock_run.return_value = MagicMock(final_output="ok")
    token, _ = _register_and_login()
    client.post("/api/assistant/chat", headers=_auth(token),
                json={"message": "a", "conversation_id": "conv-1"})
    _, kw1 = mock_run.call_args
    client.post("/api/assistant/chat", headers=_auth(token),
                json={"message": "b", "conversation_id": "conv-2"})
    _, kw2 = mock_run.call_args
    me = client.get("/api/auth/me", headers=_auth(token)).json()
    uid = me["id"]
    assert kw1["session"].session_id == f"{uid}:conv-1"
    assert kw2["session"].session_id == f"{uid}:conv-2"
    assert kw1["session"].session_id != kw2["session"].session_id
    print("[PASS] assistant chat: conversation IDs isolated per user")


# ---------------------------------------------------------------------------
# Security: ownership + price manipulation resistance
# ---------------------------------------------------------------------------

def test_booking_client_user_id_ignored(sync_flight_id):
    """Client-supplied user_id in booking request cannot bypass ownership."""
    token_a, _ = _register_and_login()
    me_a = client.get("/api/auth/me", headers=_auth(token_a)).json()
    # Attempt to book disguised as another user via body field
    r = client.post("/api/bookings", headers=_auth(token_a), json={
        "flight_id": sync_flight_id,
        "user_id": "attacker-controlled-id",
        "passengers": [{
            "first_name": "Jane", "last_name": "Doe",
            "passenger_type": "adult", "date_of_birth": "1991-02-02",
        }],
    })
    # user_id is not an accepted field; extra fields ignored / 422 — regardless,
    # the created booking must be owned by the token user.
    if r.status_code == 201:
        booking = r.json()
        assert booking["user_id"] == me_a["id"]
        assert booking["user_id"] != "attacker-controlled-id"
    else:
        assert r.status_code == 422, r.text  # extra user_id rejected by schema
    print("[PASS] security: client user_id cannot bypass booking ownership")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests():
    import asyncio
    asyncio.run(init_db())
    flight_id = asyncio.run(_create_flight())

    # Tests that need a flight id take sync_flight_id kwarg
    tests = [
        ("register_no_hash", test_register_returns_no_password_hash, {}),
        ("register_duplicate_409", test_register_duplicate_returns_409, {}),
        ("register_invalid_422", test_register_invalid_data_returns_422, {}),
        ("login_success", test_login_success_returns_token, {}),
        ("login_wrong_401", test_login_wrong_password_returns_401, {}),
        ("me_requires_auth", test_me_requires_auth, {}),
        ("me_safe_user", test_me_returns_safe_user, {}),
        ("invalid_token", test_invalid_token_rejected, {}),
        ("flight_requires_auth", test_flight_endpoints_require_auth, {}),
        ("flight_details_404", test_flight_details_404, {"sync_flight_id": flight_id}),
        ("flight_search_price", test_flight_search_and_price, {"sync_flight_id": flight_id}),
        ("seat_availability", test_seat_availability, {"sync_flight_id": flight_id}),
        ("booking_requires_auth", test_booking_requires_auth, {}),
        ("booking_create_get", test_booking_create_and_get, {"sync_flight_id": flight_id}),
        ("booking_ownership", test_booking_ownership_isolation, {"sync_flight_id": flight_id}),
        ("booking_list_own", test_booking_list_only_own, {"sync_flight_id": flight_id}),
        ("payment_requires_auth", test_payment_requires_auth, {}),
        ("payment_db_price", test_payment_checkout_uses_db_price, {"sync_flight_id": flight_id}),
        ("payment_ownership", test_payment_ownership_enforced, {"sync_flight_id": flight_id}),
        ("webhook_bad_sig", test_webhook_rejects_bad_signature, {}),
        ("assistant_requires_auth", test_assistant_requires_auth, {}),
        ("assistant_chat_context", test_assistant_chat_with_context, {}),
        ("assistant_user_from_token", test_assistant_user_from_token_not_request, {}),
        ("assistant_conversation_isolation", test_assistant_conversation_isolation, {}),
        ("booking_client_user_id_ignored", test_booking_client_user_id_ignored, {"sync_flight_id": flight_id}),
    ]

    print("=" * 70)
    print("PHASE 14 - HTTP API ENDPOINT TESTS")
    print("=" * 70)

    passed = failed = 0
    for name, fn, kwargs in tests:
        try:
            fn(**kwargs)
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULT: {passed} passed, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
