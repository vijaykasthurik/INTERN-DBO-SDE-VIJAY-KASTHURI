import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FFFFFF",
        surface: "#FAFAFB",
        panel: "#FAFAFB",
        ink: {
          DEFAULT: "#0B0B0F",
          muted: "#6B7280",
          faint: "#9CA3AF",
        },
        hairline: "rgba(15, 23, 42, 0.08)",
        accent: {
          indigo: "#6366F1",
          violet: "#8B5CF6",
          cyan: "#22D3EE",
        },
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #22D3EE 100%)",
        "accent-gradient-hover": "linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #06B6D4 100%)",
        "radial-glow": "radial-gradient(circle at center, rgba(99, 102, 241, 0.15) 0%, transparent 70%)",
      },
      boxShadow: {
        "soft-xs": "0 1px 2px rgba(15, 23, 42, 0.04)",
        "soft-sm": "0 2px 8px rgba(15, 23, 42, 0.04)",
        "soft-md": "0 8px 30px rgba(15, 23, 42, 0.06)",
        "soft-lg": "0 16px 40px rgba(15, 23, 42, 0.08)",
        "nav-glow": "0 4px 20px -2px rgba(99, 102, 241, 0.2)",
      },
      borderRadius: {
        "16": "16px",
        "20": "20px",
        "24": "24px",
        "28": "28px",
        "pill": "9999px",
      },
      fontFamily: {
        sans: ["'Inter Variable'", "Inter", "-apple-system", "sans-serif"],
        serif: ["'Instrument Serif'", "Georgia", "serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
        tighter: "-0.02em",
        tight: "-0.01em",
      },
      animation: {
        "border-glow": "rotate-glow 8s linear infinite",
        "shimmer": "shimmer 2s infinite linear",
      },
      keyframes: {
        "rotate-glow": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
