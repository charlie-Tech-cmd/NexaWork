export type IconName =
  | "arrow"
  | "message"
  | "channels"
  | "announcement"
  | "video"
  | "file"
  | "spark"
  | "people"
  | "shield"
  | "check"
  | "globe"
  | "chevron"
  | "overview"
  | "structure"
  | "building"
  | "settings"
  | "menu"
  | "logout";
const paths: Record<IconName, React.ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  structure: (
    <>
      <rect x="8" y="2" width="8" height="6" rx="1" />
      <path d="M12 8v5M5 16v-3h14v3" />
      <rect x="2" y="16" width="6" height="6" rx="1" />
      <rect x="16" y="16" width="6" height="6" rx="1" />
    </>
  ),
  building: (
    <>
      <path d="M4 21V3h12v18M16 9h4v12M2 21h20M8 7h4M8 11h4M8 15h4M9 21v-3h2v3" />
    </>
  ),
  settings: (
    <>
      <path d="M3 7h9m6 0h3M3 17h3m6 0h9" />
      <circle cx="15" cy="7" r="3" />
      <circle cx="9" cy="17" r="3" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  logout: (
    <>
      <path d="M10 3H4v18h6M10 12h11m-5-5 5 5-5 5" />
    </>
  ),
  arrow: (
    <>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </>
  ),
  message: (
    <>
      <path d="M21 11a8 8 0 0 1-8 8H7l-5 3V11a9 9 0 0 1 19 0Z" />
      <path d="M7 9h9M7 13h6" />
    </>
  ),
  channels: (
    <>
      <path d="M4 8h16M3 16h16M10 3 6 21M18 3l-4 18" />
    </>
  ),
  announcement: (
    <>
      <path d="m4 9 16-5v16L4 15V9ZM4 10H2v4h2M8 16l1 5h4l-2-4" />
    </>
  ),
  video: (
    <>
      <rect x="2" y="5" width="14" height="14" rx="3" />
      <path d="m16 10 6-4v12l-6-4" />
    </>
  ),
  file: (
    <>
      <path d="M14 2H5a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9l-7-7Z" />
      <path d="M14 2v7h7M7 14h10M7 18h7" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4M18 4h4" />
    </>
  ),
  people: (
    <>
      <circle cx="9" cy="7" r="3" />
      <path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4v3" />
    </>
  ),
  shield: (
    <>
      <path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Z" />
      <path d="m8 12 3 3 5-6" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <ellipse cx="12" cy="12" rx="4" ry="9" />
      <path d="M3 12h18" />
    </>
  ),
  chevron: <path d="m9 5 7 7-7 7" />,
};
export function Icon({ name }: { name: IconName }) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}
