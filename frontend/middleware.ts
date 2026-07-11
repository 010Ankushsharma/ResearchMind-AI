import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Routes that do NOT require authentication:
 *   - Clerk's own sign-in/sign-up pages (and their sub-routes)
 *   - The Clerk webhook receiver (authenticated via Svix signature, not a user session)
 *   - The health check endpoint
 *
 * Everything else (Home, Research Workspace, Knowledge Base, Analytics,
 * Settings, and all other /api/* calls) requires a signed-in Clerk session.
 */
const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/auth/webhook",
  "/api/health",
]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
