// Messaging and private files are implemented in PR #8; uploads require workspace enablement.
export const features = [
  {
    icon: "message",
    title: "Team Messaging",
    description:
      "Start a direct or group conversation, share updates, and return to earlier messages whenever you need the context.",
    status: "Available now",
  },
  {
    icon: "file",
    title: "Private File Sharing",
    description:
      "Share documents with a message and find them in the conversation’s Files tab. Downloads are limited to conversation members.",
    status: "Available when enabled",
  },
  {
    icon: "channels",
    title: "Channels and Collaboration",
    description: "Keep project and department discussions organized.",
    status: "Planned",
  },
  {
    icon: "announcement",
    title: "Company Announcements",
    description: "Share important updates across the organization.",
    status: "Planned",
  },
  {
    icon: "video",
    title: "Meetings",
    description: "Bring colleagues together for virtual collaboration.",
    status: "Planned",
  },
  {
    icon: "spark",
    title: "AI Workplace Assistant",
    description: "Help employees find information and work more efficiently.",
    status: "Planned",
  },
] as const;
export const navigation = [
  { label: "Product", href: "#product" },
  { label: "Features", href: "#features" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "#contact" },
] as const;
export const dayScenes = [
  {
    title: "Bring your people into the picture.",
    description:
      "Set up your organization, add colleagues, and give regions, departments and teams a clear place to belong.",
    status: "Available now",
    icon: "people",
    label: "Workspace structure",
    rows: ["Your organization", "Regions & branches", "Departments & teams"],
  },
  {
    title: "Keep the conversation moving.",
    description:
      "Message a colleague directly or bring the team into a group conversation. Keep separate drafts and pick up earlier discussions without losing the context.",
    status: "Available now",
    icon: "message",
    label: "Team conversation",
    rows: [
      "Design team",
      "Share an idea with your team",
      "Keep the conversation in context",
    ],
  },
  {
    title: "Keep files with the conversation.",
    description:
      "Attach a document, add a message, and share it with the people in your conversation. Open the Files tab to find and download shared documents once file sharing is enabled for your workspace.",
    status: "Available when enabled",
    icon: "file",
    label: "Conversation files",
    rows: [
      "Project discussion",
      "Review notes.pdf",
      "Download shared documents",
    ],
  },
  {
    title: "Keep everyone in the loop.",
    description:
      "The vision: managers share company updates in one place, so every department has the same context.",
    status: "Planned",
    icon: "announcement",
    label: "Company update",
    rows: [
      "Company announcements",
      "An update for everyone",
      "One place for important information",
    ],
  },
] as const;
export function publicView(
  pathname: string,
): "landing" | "login" | "onboard" | "reset" | "workspace" | "not-found" {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/") return "landing";
  if (path === "/sign-in") return "login";
  if (path === "/get-started") return "onboard";
  if (path === "/reset-password") return "reset";
  if (path === "/workspace") return "workspace";
  return "not-found";
}

export function resetTokenFromSearch(search: string): string {
  return new URLSearchParams(search).get("token")?.trim() || "";
}
