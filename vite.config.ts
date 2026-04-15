import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Ajuste o base para o nome do seu repositório no GitHub
// Ex: se o repo for "github.com/usuario/anbima-dashboard", use "/anbima-dashboard/"
// Para dev local, use "/"
const base = process.env.GITHUB_REPOSITORY
  ? `/${process.env.GITHUB_REPOSITORY.split("/")[1]}/`
  : "/";

export default defineConfig({
  plugins: [react()],
  base,
});
