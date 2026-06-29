import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#0a0a14",
          secondary: "#111127",
          card: "#16162a",
          sidebar: "#0d0d1f",
          hover: "#1e1e35",
          border: "#2a2a45",
        },
        accent: {
          green: "#00d084",
          "green-dim": "#00a866",
          purple: "#7c5cfc",
          "purple-dim": "#5a42d4",
          gold: "#f5a623",
          red: "#ff4757",
          blue: "#3d9df3",
        },
        text: {
          primary: "#e8e8f0",
          secondary: "#9898b8",
          muted: "#5a5a7a",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
