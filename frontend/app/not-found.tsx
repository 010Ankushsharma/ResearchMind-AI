import Link from "next/link";
import { Compass } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Next.js App Router convention file — rendered for any unmatched route
 * across the whole app (outside any specific route group's own not-found).
 */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background bg-gradient-radial-glow px-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/15">
        <Compass className="h-6 w-6 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold text-foreground">Page not found</h1>
      <p className="max-w-sm text-sm text-foreground-muted">
        The page you&apos;re looking for doesn&apos;t exist or may have been moved.
      </p>
      <Button asChild variant="gradient">
        <Link href="/">Back to Home</Link>
      </Button>
    </div>
  );
}
