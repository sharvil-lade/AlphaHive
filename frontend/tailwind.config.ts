import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Vercel Geist-inspired neutral palette — clean, minimal, no glow/glass.
        // Values are CSS variables (see globals.css) so light/dark mode can swap
        // them at runtime via the .dark class, without any component changes.
        background: "rgb(var(--color-background) / <alpha-value>)",
        foreground: "rgb(var(--color-foreground) / <alpha-value>)",

        surface: {
          DEFAULT: "rgb(var(--color-surface) / <alpha-value>)",
          raised: "rgb(var(--color-surface-raised) / <alpha-value>)",
          hover: "rgb(var(--color-surface-hover) / <alpha-value>)",
          border: "rgb(var(--color-surface-border) / <alpha-value>)",
        },

        // Financial semantic accents — kept even in a neutral design system,
        // since red/green deltas are a hard requirement for this domain.
        bullish: { DEFAULT: "rgb(var(--color-bullish) / <alpha-value>)" },
        bearish: { DEFAULT: "rgb(var(--color-bearish) / <alpha-value>)" },
        accent: { DEFAULT: "rgb(var(--color-foreground) / <alpha-value>)" },

        mutedText: "rgb(var(--color-muted) / <alpha-value>)",
      },

      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },

      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        popover: "0 4px 24px -4px rgba(0, 0, 0, 0.5)",
      },

      borderRadius: {
        lg: "10px",
        md: "8px",
        sm: "6px",
      },

      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.2s ease-out",
      },

      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(6px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
