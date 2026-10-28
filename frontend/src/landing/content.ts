// Verified against main a39b177. Keep marketing availability tied to released routes.
export const plannedFeatures = [
  {
    icon: "message",
    title: "Team Messaging",
    description: "Organized conversations for employees and teams.",
  },
  {
    icon: "channels",
    title: "Channels and Collaboration",
    description: "Keep project and department discussions organized.",
  },
  {
    icon: "announcement",
    title: "Company Announcements",
    description: "Share important updates across the organization.",
  },
  {
    icon: "video",
    title: "Meetings",
    description: "Bring colleagues together for virtual collaboration.",
  },
  {
    icon: "file",
    title: "File Sharing",
    description: "Make work-related documents easier to access and share.",
  },
  {
    icon: "spark",
    title: "AI Workplace Assistant",
    description: "Help employees find information and work more efficiently.",
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
      "The vision: a colleague asks a question, the team shares context, and project conversations stay easy to follow.",
    status: "Planned",
    icon: "message",
    label: "Team conversation",
    rows: [
      "Design team",
      "Share an idea with your team",
      "Keep the conversation in context",
    ],
  },
  {
    title: "Make space to work together.",
    description:
      "The vision: move from a discussion to a meeting, share the relevant documents, and find the information you need.",
    status: "Planned",
    icon: "video",
    label: "A collaborative afternoon",
    rows: ["Project discussion", "Team catch-up", "Shared documents"],
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
