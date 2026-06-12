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
        coach: {
          blue: "#5680E9",
          sky: "#84CEEB",
          cyan: "#5AB9EA",
          mist: "#C1C8E4",
          violet: "#8860D0",
        },
      },
      backgroundImage: {
        "coach-page":
          "radial-gradient(ellipse 85% 55% at 5% 0%, rgba(132,206,235,0.45) 0%, transparent 55%), radial-gradient(ellipse 70% 50% at 100% 5%, rgba(136,96,208,0.2) 0%, transparent 50%), radial-gradient(ellipse 65% 45% at 50% 100%, rgba(90,185,234,0.28) 0%, transparent 55%), linear-gradient(160deg, #e4eaf8 0%, #f8f9fd 38%, #eef1f9 68%, #e2f3fb 100%)",
        "coach-sidebar":
          "linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(193,200,228,0.12) 50%, rgba(132,206,235,0.1) 100%)",
        "coach-card":
          "linear-gradient(135deg, rgba(238,242,252,0.95) 0%, rgba(255,255,255,0.98) 45%, rgba(240,235,248,0.9) 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
