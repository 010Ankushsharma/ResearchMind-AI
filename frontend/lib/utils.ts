import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes safely — combines conditional classnames (clsx)
 * with conflict resolution (tailwind-merge) so later classes correctly
 * override earlier ones (e.g. `cn("p-4", isActive && "p-6")` -> "p-6").
 * Required by every shadcn/ui-style component.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formats a 0-100 score as a rounded percentage string, e.g. "87%". */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return "—";
  return `${Math.round(score)}%`;
}

/** Maps a 0-100 trustworthiness/confidence score to a semantic Badge variant. */
export function scoreToColor(score: number | null | undefined): "success" | "warning" | "danger" | "default" {
  if (score === null || score === undefined) return "default";
  if (score >= 75) return "success";
  if (score >= 50) return "warning";
  return "danger";
}

/** Relative time string for timestamps, e.g. "2m ago", "3h ago", "5d ago". */
export function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const diffMs = Date.now() - date.getTime();
  const diffSeconds = Math.round(diffMs / 1000);

  if (diffSeconds < 60) return "just now";
  const diffMinutes = Math.round(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/** Truncates a string to a max length, appending an ellipsis if cut. */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trimEnd()}…`;
}

/** Extracts a clean display domain from a URL (strips protocol + www). */
export function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Turns a snake_case agent/status name into a readable label, e.g. "web_research" -> "Web Research". */
export function humanizeSnakeCase(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
