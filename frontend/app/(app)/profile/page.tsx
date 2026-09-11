import type { Metadata } from "next";

import { ProfileView } from "@/components/profile/ProfileView";

export const metadata: Metadata = {
  title: "Profile | Flight Assistant AI",
  description: "Your Flight Assistant AI profile.",
};

export default function ProfilePage() {
  return <ProfileView />;
}