import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        anbima: {
          blue: "#1B3157",         // Azul Profundidade 1 - Icatu Vanguarda
          "blue-dark": "#0D6696",  // Azul Profundidade 2
          "blue-3": "#2E96BF",     // Azul Profundidade 3
          "blue-4": "#00BADB",     // Azul Profundidade 4
          "blue-light": "#EBF5FB", // tint para fundos
          green: "#5FBB47",        // Verde Vanguarda
          gray: "#E6E7E8",         // Cinza Vanguarda
        },
      },
      fontFamily: {
        sans: ["Palanquin", "Verdana", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
