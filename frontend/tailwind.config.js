/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Section 11: restrained palette — one accent color + neutrals.
        accent: {
          50: "#eef2ff",
          100: "#e0e7ff",
          500: "#4f46e5",
          600: "#4338ca",
          700: "#3730a3",
        },
        ink: {
          900: "#1a1c23",
          700: "#2d3142",
          500: "#4a4e5c",
          300: "#9297a5",
          100: "#e4e6eb",
          50: "#f7f8fa",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};