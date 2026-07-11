/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Enables the lightweight `.next/standalone` server bundle consumed by
  // the production stage of frontend/Dockerfile (just `node server.js`,
  // no full node_modules copy needed in the final image).
  output: "standalone",

  // Proxy /api/* calls to the FastAPI backend during development so the
  // frontend can call relative paths (e.g. fetch("/api/research")) without
  // hardcoding the backend origin or running into CORS in the browser.
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "img.clerk.com" },
      { protocol: "https", hostname: "images.clerk.dev" },
    ],
  },
};

module.exports = nextConfig;
