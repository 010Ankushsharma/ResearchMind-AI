import type { Config } from "tailwindcss";

/**
 * Tailwind theme for the Multi-Agent Research & Report Generation Platform.
 *
 * Palette and style follow the platform spec directly: a premium dark-mode
 * "modern AI SaaS" look in the spirit of Perplexity / OpenAI / Notion / Linear.
 */
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B1120",
        card: "#111827",
        border: "#1F2937",
        muted: "#6B7280",

        primary: {
          DEFAULT: "#3B82F6",
          foreground: "#F9FAFB",
          hover: "#2563EB",
        },
        accent: {
          DEFAULT: "#8B5CF6",
          foreground: "#F9FAFB",
          hover: "#7C3AED",
        },
        success: {
          DEFAULT: "#22C55E",
          foreground: "#052E14",
        },
        warning: {
          DEFAULT: "#F59E0B",
          foreground: "#451A03",
        },
        danger: {
          DEFAULT: "#EF4444",
          foreground: "#450A0A",
        },

        foreground: "#E5E7EB",
        "foreground-muted": "#9CA3AF",
      },

      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
      },

      borderRadius: {
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
      },

      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.4), 0 1px 3px 1px rgb(0 0 0 / 0.2)",
        glow: "0 0 0 1px rgb(59 130 246 / 0.4), 0 0 24px -4px rgb(59 130 246 / 0.35)",
        "glow-accent": "0 0 0 1px rgb(139 92 246 / 0.4), 0 0 24px -4px rgb(139 92 246 / 0.35)",
      },

      backgroundImage: {
        "gradient-primary-accent": "linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%)",
        "gradient-radial-glow":
          "radial-gradient(circle at 50% 0%, rgba(59,130,246,0.15), transparent 60%)",
      },

      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "agent-typing": {
          "0%, 100%": { transform: "scaleY(1)" },
          "50%": { transform: "scaleY(0.4)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.4s ease-in-out infinite",
        "fade-in": "fade-in 0.2s ease-out",
        "agent-typing": "agent-typing 0.9s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
