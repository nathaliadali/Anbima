import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        anbima: {
          blue: "#003DA5",
          "blue-dark": "#002D7A",
          "blue-light": "#E8F0FF",
          green: "#00843D",
          gray: "#F5F5F5",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
