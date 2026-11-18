import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#0a0e14", 900: "#0d1117", 800: "#131a24", 700: "#1a2230", 600: "#243042" },
        line: "#263142",
        accent: "#ecad0a",
        primary: "#209dd7",
        secondary: "#753991",
        up: "#26d07c",
        down: "#ff5470",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
