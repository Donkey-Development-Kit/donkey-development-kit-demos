import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the Starlette backend on :8000 so the SPA and the
// governed agent share an origin (no CORS dance during development).
// VITE_BASE is the GitHub Pages sub-path (/<repo>/); local builds serve from /.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
