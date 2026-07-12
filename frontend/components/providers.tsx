"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

/**
 * Client-side providers wrapper.
 *
 * Kept separate from app/layout.tsx (a server component) since React Query's
 * QueryClient and other client-only providers must be instantiated inside a
 * "use client" boundary.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000, // 30s — research session/agent status polls override this per-query
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#111827",
            border: "1px solid #1F2937",
            color: "#E5E7EB",
          },
        }}
      />
    </QueryClientProvider>
  );
}
