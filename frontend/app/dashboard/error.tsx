"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Next.js App Router convention file — automatically wraps any page inside
 * the (dashboard) route group in an error boundary. Must be a Client
 * Component. `reset()` re-renders the segment, giving the user a one-click
 * retry without a full page reload.
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production, forward this to your error-tracking service (Sentry, etc.)
    console.error("Dashboard route error:", error);
  }, [error]);

  return (
    <div className="flex h-[60vh] items-center justify-center">
      <Card className="max-w-md">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger/15">
            <AlertTriangle className="h-6 w-6 text-danger" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Something went wrong</h2>
            <p className="mt-1 text-sm text-foreground-muted">
              {error.message || "An unexpected error occurred while loading this page."}
            </p>
          </div>
          <Button onClick={reset} variant="outline">
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
