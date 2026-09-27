import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  server: {
    port: 5183,
    strictPort: false,
    host: "127.0.0.1",
  },
  resolve: {
    alias: {
      "@bonk": "/Users/suhaas/Documents/GitHub/bonk-beta/src",
    },
  },
  esbuild: {
    jsx: "automatic",
    tsx: "automatic",
  },
});
