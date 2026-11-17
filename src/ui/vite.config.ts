import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API calls to the FastAPI backend. In production the backend serves the built files.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000", "/healthz": "http://localhost:8000" } },
  build: { outDir: "dist" },
});
