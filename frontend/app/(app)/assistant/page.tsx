import type { Metadata } from "next";

import { AssistantExperience } from "@/components/assistant/AssistantExperience";

export const metadata: Metadata = {
  title: "AI Travel Assistant | Flight Assistant AI",
  description:
    "Chat with your Flight Assistant AI to search flights, compare options, and plan your trip.",
};

export default function AssistantPage() {
  return <AssistantExperience />;
}