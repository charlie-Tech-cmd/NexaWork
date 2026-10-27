import type { MouseEventHandler } from "react";

export function Wordmark({
  className = "",
  inverse = false,
  href = "/",
  label = "NexaWork home",
  onClick,
}: {
  className?: string;
  inverse?: boolean;
  href?: string;
  label?: string;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
}) {
  return (
    <a
      href={href}
      className={`wordmark ${inverse ? "wordmark-inverse" : ""} ${className}`}
      aria-label={label}
      onClick={onClick}
    >
      Nexa<span className="wordmark-work">Work</span>
      <span className="wordmark-period">.</span>
    </a>
  );
}
