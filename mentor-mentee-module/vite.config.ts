import federation from "@originjs/vite-plugin-federation";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import type { Connect } from "vite";
import { defineConfig, loadEnv } from "vite";

/** Cross-origin `import()` of remoteEntry + chunks needs permissive CORS when the shell is not proxied. */
function federationRemoteCors(): { name: string; configureServer: (s: { middlewares: Connect.Server }) => void; configurePreviewServer: (s: { middlewares: Connect.Server }) => void } {
  const setCors: Connect.NextHandleFunction = (_req, res, next) => {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET,HEAD,OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "*");
    next();
  };
  return {
    name: "mentor-federation-cors",
    configureServer({ middlewares }) {
      middlewares.use(setCors);
    },
    configurePreviewServer({ middlewares }) {
      middlewares.use(setCors);
    },
  };
}

function userServiceProxy(): Record<string, object> {
  const target = process.env.VITE_USER_SERVICE_PROXY_TARGET || "http://127.0.0.1:8000";
  return {
    "/user-service": {
      target,
      changeOrigin: true,
      secure: false,
      ws: true,
      rewrite: (p: string) => p.replace(/^\/user-service/, "") || "/",
    },
  };
}

/** Matches `getMentoringDomainBaseUrl()` fallback `origin/mentoring-service` — wire dev server to real API. */
function mentoringServiceProxy(): Record<string, object> {
  const target =
    process.env.MENTORING_SERVICE_PROXY_TARGET ||
    process.env.VITE_MENTORING_PROXY_TARGET ||
    "https://mentoring-service-1095720168864-1095720168864.us-central1.run.app";
  return {
    "/mentoring-service": {
      target,
      changeOrigin: true,
      secure: true,
      rewrite: (p: string) => p.replace(/^\/mentoring-service/, "") || "/",
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const mfePort = Number(env.VITE_MFE_REMOTE_PORT) || 5001;

  return {
    server: {
      // `true` listens on all addresses so `http://localhost:PORT` works reliably on Windows
      // (binding only `::` can leave IPv4 `127.0.0.1` unreachable for the shell).
      host: true,
      port: mfePort,
      strictPort: true,
      cors: true,
      hmr: { overlay: false },
      proxy: { ...userServiceProxy(), ...mentoringServiceProxy() },
    },
    preview: {
      host: true,
      port: mfePort,
      strictPort: true,
      cors: true,
      proxy: { ...userServiceProxy(), ...mentoringServiceProxy() },
    },
    plugins: [
      federationRemoteCors(),
      react(),
      federation({
        name: "mentorMentee",
        filename: "remoteEntry.js",
        exposes: {
          "./App": "./src/App.tsx",
        },
        shared: ["react", "react-dom", "react-router-dom"],
      }),
    ],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
      dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime", "react-router-dom"],
    },
    build: {
      target: "esnext",
      modulePreload: false,
      cssCodeSplit: true,
    },
  };
});
