/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#080c16", 900: "#0b1120", 800: "#101829", 700: "#162036", 600: "#1e2a45", 500: "#2a3858" },
        accent: { DEFAULT: "#6366f1", soft: "#818cf8" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
