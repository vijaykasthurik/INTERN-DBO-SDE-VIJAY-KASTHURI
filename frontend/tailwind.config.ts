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
          DEFAULT: "#059669",
          emerald: "#059669",
          dark: "#047857",
          light: "#D1FAE5",
          muted: "#ECFDF5",
          indigo: "#059669",
          violet: "#047857",
          cyan: "#059669",
        },
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, #0B0B0F 0%, #1E293B 100%)",
        "accent-gradient-hover": "linear-gradient(135deg, #1E293B 0%, #334155 100%)",
        "radial-glow": "radial-gradient(circle at center, rgba(5, 150, 105, 0.08) 0%, transparent 70%)",
      },
      boxShadow: {
        "soft-xs": "0 1px 2px rgba(15, 23, 42, 0.04)",
        "soft-sm": "0 2px 8px rgba(15, 23, 42, 0.04)",
        "soft-md": "0 8px 30px rgba(15, 23, 42, 0.06)",
        "soft-lg": "0 16px 40px rgba(15, 23, 42, 0.08)",
        "nav-glow": "0 4px 20px -2px rgba(11, 11, 15, 0.08)",
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
