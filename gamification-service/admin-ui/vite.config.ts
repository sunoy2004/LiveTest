import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/** Dev uses base `/` so `/admin/*` matches `server.proxy`. Production build keeps `/ui/` for FastAPI StaticFiles. */
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.VITE_GAMIFICATION_API_PROXY || "http://127.0.0.1:8002";

  const proxy = {
    target: apiProxyTarget,
    changeOrigin: true,
    secure: false,
  };

  return {
    plugins: [react()],
    base: command === "build" ? "/ui/" : "/",
    build: {
      outDir: "../app/static/admin",
      emptyOutDir: true,
    },
    server: {
      port: 5176,
      strictPort: true,
      proxy: {
        "/admin": { ...proxy },
        "/wallet": { ...proxy },
        "/internal": { ...proxy },
        "/balance": { ...proxy },
        "/deduct": { ...proxy },
        "/add": { ...proxy },
        "/health": { ...proxy },
        "/api": { ...proxy },
        "/openapi.json": { ...proxy },
        "/docs": { ...proxy },
        "/redoc": { ...proxy },
      },
    },
  };
});
