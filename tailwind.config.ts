import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#ff4b4b",
          dark: "#e63b3b",
        },
      },
    },
  },
  plugins: [],
};

export default config;
