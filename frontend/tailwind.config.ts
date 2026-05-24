import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#080c14",
        foreground: "#f3f4f6",
        terminal: {
          dark: "#0b0f19",
          card: "rgba(15, 22, 38, 0.65)",
          border: "rgba(255, 255, 255, 0.06)",
          hover: "rgba(255, 255, 255, 0.1)",
        },
        bullish: {
          DEFAULT: "#10b981", // Emerald Green
          glow: "rgba(16, 185, 129, 0.15)",
        },
        bearish: {
          DEFAULT: "#f43f5e", // Rose Red
          glow: "rgba(244, 63, 94, 0.15)",
        },
        cyanGlow: {
          DEFAULT: "#06b6d4", // Electric Cyan
          glow: "rgba(6, 182, 212, 0.15)",
        },
        mutedText: "#9ca3af",
      },
      backdropBlur: {
        xs: "2px",
      },
      boxShadow: {
        glow: "0 0 20px rgba(6, 182, 212, 0.15)",
        terminal: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      animation: {
        "pulse-cyan": "pulseCyan 2s infinite",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        pulseCyan: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: ".5", transform: "scale(1.05)" },
        },
        slideUp: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
