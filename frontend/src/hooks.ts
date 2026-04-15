import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  CandlesResponse,
  AccuracyResponse,
  ExplanationResponse,
  Analog,
  PredictionData,
  AgentsStatsResponse,
  WeightHistoryEntry,
} from './types';

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '';

/* ── Generic fetcher with error handling ── */
async function fetchJSON<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${url}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/* ── usePolling: generic polling hook ── */
function usePolling<T>(
  fetcher: () => Promise<T | null>,
  intervalMs: number,
): { data: T | null; loading: boolean; error: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      const result = await fetcherRef.current();
      if (!mounted) return;
      if (result !== null) {
        setData(result);
        setError(false);
      } else {
        setError(true);
      }
      setLoading(false);
    };

    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { data, loading, error };
}

/* ── Candles hook ── */
export function useCandles(limit = 100, intervalMs = 60_000) {
  const fetcher = useCallback(
    () => fetchJSON<CandlesResponse>(`/api/candles?limit=${limit}`),
    [limit],
  );
  return usePolling(fetcher, intervalMs);
}

/* ── Accuracy hook ── */
export function useAccuracy(intervalMs = 60_000) {
  const fetcher = useCallback(
    () => fetchJSON<AccuracyResponse>('/api/feedback/accuracy'),
    [],
  );
  return usePolling(fetcher, intervalMs);
}

/* ── Explanation hook ── */
export function useExplanation(intervalMs = 60_000) {
  const fetcher = useCallback(
    () => fetchJSON<ExplanationResponse>('/api/explanation/latest'),
    [],
  );
  return usePolling(fetcher, intervalMs);
}

/* ── Analogs hook (uses candles to derive recent window) ── */
export function useAnalogs(intervalMs = 60_000) {
  const fetcher = useCallback(
    () => fetchJSON<Analog[]>('/api/analogs?top_n=3'),
    [],
  );
  return usePolling(fetcher, intervalMs);
}

/* ── Live prediction hook: WebSocket primary, REST fallback ── */
export function useLivePrediction(fallbackIntervalMs = 30_000): {
  data: PredictionData | null;
  loading: boolean;
  connected: boolean;
} {
  const [data, setData] = useState<PredictionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const fallbackTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchFallback = useCallback(async () => {
    const result = await fetchJSON<PredictionData>('/api/prediction');
    if (mountedRef.current && result !== null) {
      setData(result);
      setLoading(false);
    }
  }, []);

  const startFallbackPolling = useCallback(() => {
    if (fallbackTimerRef.current !== null) return;
    fetchFallback();
    fallbackTimerRef.current = setInterval(fetchFallback, fallbackIntervalMs);
  }, [fetchFallback, fallbackIntervalMs]);

  const stopFallbackPolling = useCallback(() => {
    if (fallbackTimerRef.current !== null) {
      clearInterval(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    const wsBase = API_BASE
      ? API_BASE.replace(/^https?/, (m) => (m === 'https' ? 'wss' : 'ws'))
      : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
    const wsUrl = `${wsBase}/ws/predictions`;

    function connect() {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        stopFallbackPolling();
      };

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return;
        try {
          const msg = JSON.parse(event.data as string) as { type: string; data: PredictionData };
          if (msg.type === 'prediction') {
            setData(msg.data);
            setLoading(false);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        startFallbackPolling();
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        startFallbackPolling();
        // Attempt reconnect after 10s
        setTimeout(() => {
          if (mountedRef.current) connect();
        }, 10_000);
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      stopFallbackPolling();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [startFallbackPolling, stopFallbackPolling]);

  return { data, loading, connected };
}

/* ── Agent stats hook ── */
export function useAgentsStats(intervalMs = 60_000) {
  const fetcher = useCallback(
    () => fetchJSON<AgentsStatsResponse>('/api/agents/stats'),
    [],
  );
  return usePolling(fetcher, intervalMs);
}

/* ── Weight history hook ── */
export function useWeightHistory(agentName: string) {
  const fetcher = useCallback(
    () => fetchJSON<WeightHistoryEntry[]>(`/api/weights/history?agent=${encodeURIComponent(agentName)}&limit=10`),
    [agentName],
  );
  return usePolling(fetcher, 300_000); // refresh every 5 min
}
