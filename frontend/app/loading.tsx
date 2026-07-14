import { Loader2 } from "lucide-react";

/**
 * Root-level loading fallback — covers any route not already covered by a
 * more specific loading.tsx (e.g. the (dashboard) group has its own richer
 * version). Used for sign-in/sign-up and any top-level route.
 */
export default function RootLoading() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background text-foreground-muted">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <p className="text-sm">Loading…</p>
    </div>
  );
}
