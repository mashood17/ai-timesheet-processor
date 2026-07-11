/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Refined indigo accent — Linear/Stripe-adjacent, single accent hue only.
        accent: {
          50: "#F5F5FF",
          100: "#ECEBFF",
          200: "#D9D8FF",
          300: "#B8B6FA",
          400: "#8B87F0",
          500: "#5B5FEF",
          600: "#4C4FDB",
          700: "#3F41B8",
        },
        // Neutral scale used for text, borders, backgrounds.
        ink: {
          950: "#0B0C10",
          900: "#12141B",
          800: "#1D2029",
          700: "#2B2E38",
          600: "#3F4250",
          500: "#5B5E6D",
          400: "#7C7F8C",
          300: "#A3A6B0",
          200: "#CBCDD4",
          100: "#E4E5EA",
          50: "#F7F7F9",
        },
        emerald: {
          50: "#ECFDF5",
          600: "#059669",
          700: "#047857",
        },
        amber: {
          50: "#FFFBEB",
          200: "#FDE68A",
          600: "#D97706",
          800: "#92400E",
        },
        red: {
          50: "#FEF2F2",
          100: "#FEE2E2",
          600: "#DC2626",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "system-ui", "sans-serif"],
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1.1rem", letterSpacing: "0.01em" }],
        sm: ["0.8125rem", { lineHeight: "1.25rem" }],
        base: ["0.9375rem", { lineHeight: "1.5rem" }],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 17, 23, 0.04), 0 1px 1px rgba(15, 17, 23, 0.03)",
        "card-hover": "0 4px 12px rgba(15, 17, 23, 0.06), 0 2px 4px rgba(15, 17, 23, 0.04)",
        popover: "0 12px 32px rgba(15, 17, 23, 0.12), 0 2px 8px rgba(15, 17, 23, 0.06)",
      },
      borderRadius: {
        xl: "0.75rem",
        "2xl": "1rem",
      },
      transitionDuration: {
        150: "150ms",
      },
    },
  },
  plugins: [],
};