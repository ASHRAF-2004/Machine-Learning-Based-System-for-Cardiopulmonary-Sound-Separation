import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Explicit local review build only. The normal application build never includes it.
export default defineConfig({
  plugins: [react()],
  define: { "import.meta.env.DEV": "true" },
  server: {
    host: "127.0.0.1",
    port: 4193,
    strictPort: true,
    watch: { ignored: ["**/output/**"] },
  },
  build: {
    outDir: "output/ux-preview-build",
    emptyOutDir: true,
    rollupOptions: {
      input: fileURLToPath(new URL("./ux-preview.html", import.meta.url)),
    },
  },
  preview: { host: "127.0.0.1", port: 4194, strictPort: true },
});
