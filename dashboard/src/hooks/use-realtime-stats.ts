"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface BotStats {
  online: boolean;
  latency_ms: number | null;
  guild_count: number;
  guilds: { id: string; name: string; member_count: number }[];
  username: string | null;
  error?: string;
}

interface UseRealtimeStatsOptions {
  enabled?: boolean;
}

export function useRealtimeStats(options: UseRealtimeStatsOptions = {}) {
  const { enabled = true } = options;
  const [stats, setStats] = useState<BotStats | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!enabled || !mountedRef.current) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const wsUrl = apiUrl.replace(/^http/, "ws") + "/ws/stats";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          setStats(data);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        wsRef.current = null;

        // Auto-reconnect after 5 seconds
        reconnectTimer.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, 5000);
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setError("WebSocket connection failed");
        setConnected(false);
      };
    } catch (err) {
      setError("Failed to connect to WebSocket");
    }
  }, [enabled]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { stats, connected, error };
}