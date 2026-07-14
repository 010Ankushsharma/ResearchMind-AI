import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Inter, JetBrains_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import "./globals.css";

const fontSans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Research Platform — AI Research & Report Generation",
  description:
    "Multi-agent AI research team that searches the web, verifies facts, and generates professional reports with citations and executive summaries.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#3B82F6",
          colorBackground: "#0B1120",
          colorInputBackground: "#111827",
          colorText: "#E5E7EB",
        },
      }}
    >
      <html lang="en" className="dark" suppressHydrationWarning>
        <body className={`${fontSans.variable} ${fontMono.variable} font-sans`}>
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
