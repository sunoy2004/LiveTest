import federation from "@originjs/vite-plugin-federation";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { defineConfig, loadEnv } from "vite";

const mentorProxyPrefix = "/__mentor_remote__";

function mentorRemoteProxy(mfePort: string): Record<string, object> {
  const target = `http://127.0.0.1:${mfePort}`;
  const userServiceTarget = process.env.VITE_USER_SERVICE_PROXY_TARGET || "http://127.0.0.1:8000";
  return {
    [mentorProxyPrefix]: {
      target,
      changeOrigin: true,
      secure: false,
      rewrite: (p: string) => p.replace(new RegExp(`^${mentorProxyPrefix}`), "") || "/",
    },
    "/user-service": {
      target: userServiceTarget,
      changeOrigin: true,
      secure: false,
      ws: true,
      rewrite: (p: string) => p.replace(/^\/user-service/, "") || "/",
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const mfePort = env.VITE_MFE_REMOTE_PORT || "5001";
  // Same-origin URL so the browser can `import()` the remote (avoids cross-origin module + CORS issues).
  // Override with VITE_MENTOR_REMOTE_ENTRY for deployed hosts that load the remote from a CDN.
  const mentorRemote =
    env.VITE_MENTOR_REMOTE_ENTRY || `${mentorProxyPrefix}/remoteEntry.js`;

  return {
    server: {
      host: true,
      port: 3000,
      strictPort: true,
      cors: true,
      proxy: mentorRemoteProxy(mfePort),
    },
    preview: {
      host: true,
      port: 3000,
      strictPort: true,
      cors: true,
      proxy: mentorRemoteProxy(mfePort),
    },
    plugins: [
      react(),
      federation({
        name: "commonUiShell",
        remotes: {
          mentorMentee: mentorRemote,
        },
        shared: {
          react: { singleton: true, requiredVersion: false },
          "react-dom": { singleton: true, requiredVersion: false },
          "react-router-dom": { singleton: true, requiredVersion: false },
        },
      }),
    ],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
      dedupe: ["react", "react-dom", "react-router-dom"],
    },
    build: {
      target: "esnext",
      modulePreload: false,
    },
  };
});
