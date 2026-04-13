import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  CandlesResponse,
  AccuracyResponse,
  ExplanationResponse,
  Analog,
} from './types';

const API_BASE = '';

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
