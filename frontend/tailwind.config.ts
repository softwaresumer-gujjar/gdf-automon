import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0fdf4",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          900: "#14532d",
        },
        // Theme-aware surface colors via CSS custom properties
        "c-bg":       "rgb(var(--c-bg) / <alpha-value>)",
        "c-surface":  "rgb(var(--c-surface) / <alpha-value>)",
        "c-surface-2":"rgb(var(--c-surface-2) / <alpha-value>)",
        "c-border":   "rgb(var(--c-border) / <alpha-value>)",
        "c-text":     "rgb(var(--c-text) / <alpha-value>)",
        "c-text-2":   "rgb(var(--c-text-2) / <alpha-value>)",
        "c-text-3":   "rgb(var(--c-text-3) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
