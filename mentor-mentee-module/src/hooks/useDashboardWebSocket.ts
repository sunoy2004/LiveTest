import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { getUserServiceDashboardWsUrl } from "@/api/userService";

/**
 * Subscribes to User Service dashboard events (Redis → WS) and refreshes React Query caches.
 */
export function useDashboardWebSocket(token: string | null | undefined) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return;
    let isClosed = false;
    let pingTimer: number | null = null;
    let reconnectTimer: number | null = null;
    let attempts = 0;
    let lastOpenAt = 0;
    let stopped = false;

    const connect = () => {
      if (stopped || isClosed) return;
      const url = getUserServiceDashboardWsUrl(token);
      const ws = new WebSocket(url);
      wsRef.current = ws;
      attempts += 1;

      ws.onopen = () => {
        lastOpenAt = Date.now();
        attempts = 0;
        if (pingTimer) window.clearInterval(pingTimer);
        // Keepalive: some browsers/dev proxies can drop idle WS connections.
        pingTimer = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 25_000);
      };

      ws.onmessage = () => {
        void queryClient.invalidateQueries({ queryKey: ["user-service", "dashboard"] });
        void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
        void queryClient.invalidateQueries({ queryKey: ["user-service", "profile-full"] });
        void queryClient.invalidateQueries({ queryKey: ["user-service", "scheduling-context"] });
        void queryClient.invalidateQueries({ queryKey: ["user-service", "wallet"] });
        void queryClient.invalidateQueries({ queryKey: ["gamification", "wallet"] });
        void queryClient.invalidateQueries({ queryKey: ["ai"] });
      };

      ws.onerror = () => {
        // Browser console is enough; avoid noisy UI errors.
      };

      ws.onclose = (ev) => {
        if (pingTimer) window.clearInterval(pingTimer);
        pingTimer = null;

        if (isClosed) return;
        // If auth fails (server closes with 4401), don't keep reconnecting.
        if (ev.code === 4401 || ev.code === 4403) {
          stopped = true;
          return;
        }

        // If we can't keep a socket open at all (common during page reloads / server not started),
        // stop after a few rapid failures to avoid spamming the console.
        const openDurationMs = lastOpenAt ? Date.now() - lastOpenAt : 0;
        if (openDurationMs < 1000 && attempts >= 5) {
          stopped = true;
          return;
        }

        // Light reconnect loop for dev (server restarts, page transitions, etc.)
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        reconnectTimer = window.setTimeout(connect, 1500);
      };
    };

    connect();
    return () => {
      isClosed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (pingTimer) window.clearInterval(pingTimer);
      const ws = wsRef.current;
      ws?.close();
      wsRef.current = null;
    };
  }, [token, queryClient]);
}
