/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF7",
        ink: "#14171F",
        slate: "#5B6472",
        line: "#E3E0D6",
        teal: {
          DEFAULT: "#0E8A82",
          dark: "#0B6D67",
          light: "#E3F3F1",
        },
        amber: {
          DEFAULT: "#DE9B34",
          light: "#FBF0DD",
        },
        coral: {
          DEFAULT: "#D5563F",
          light: "#FBE7E2",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        lg: "10px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(20,23,31,0.06)",
      },
    },
  },
  plugins: [],
};
