"use client";

import { AssistantProvider } from "@/lib/assistant/assistant-context";

import { AssistantShell } from "./AssistantShell";

export function AssistantExperience() {
  return (
    <AssistantProvider>
      <AssistantShell />
    </AssistantProvider>
  );
}