import { Loader2 } from "lucide-react";

/**
 * Next.js App Router convention file — automatically shown as a
 * suspense fallback while any page inside the (dashboard) route group
 * is loading (e.g. during navigation or server data fetching).
 */
export default function DashboardLoading() {
  return (
    <div className="flex h-[60vh] flex-col items-center justify-center gap-3 text-foreground-muted">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <p className="text-sm">Loading…</p>
    </div>
  );
}
