import { useEffect, useMemo, useRef, useState } from 'react';
import {
  CandlestickSeries,
  LineSeries,
  LineStyle,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from 'lightweight-charts';
import { useIntradayCandles, useLivePrediction } from '../hooks';
import type { CandleData, PredictionData, PredictionZone } from '../types';

const CHART_HEIGHT = 390;
const CLOCK_UPDATE_INTERVAL_MS = 30_000;
const HIGH_CONFIDENCE_THRESHOLD = 70;
const MEDIUM_CONFIDENCE_THRESHOLD = 40;

function toUtcTimestamp(value: number): UTCTimestamp {
  return value as UTCTimestamp;
}

function toChartCandle(candle: CandleData): CandlestickData<UTCTimestamp> {
  return {
    time: toUtcTimestamp(candle.time),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  };
}

function normalizeDirection(direction: string): PredictionZone['direction'] {
  const normalized = direction.toLowerCase();
  if (normalized === 'buy' || normalized === 'up') return 'BUY';
  if (normalized === 'sell' || normalized === 'down') return 'SELL';
  return 'HOLD';
}

function normalizeConfidence(confidence: number): number {
  if (confidence <= 1) return Math.max(0, Math.min(confidence, 1));
  return Math.max(0, Math.min(confidence / 100, 1));
}

function buildPredictionZone(lastCandle: CandleData | null, prediction: PredictionData | null): PredictionZone | null {
  if (!lastCandle || !prediction) return null;
  const direction = normalizeDirection(prediction.predicted_direction);
  const confidence = normalizeConfidence(prediction.confidence);
  const minutes = prediction.timeframe_minutes > 0 ? prediction.timeframe_minutes : 15;
  return {
    direction,
    target_time: lastCandle.time + minutes * 60,
    confidence,
    regime: prediction.regime,
  };
}

function getRegimeBadge(regime: string): { label: string; className: string } {
  const normalized = regime.toLowerCase();
  if (normalized.includes('crisis')) {
    return { label: '🔴 Crisis', className: 'bg-red-600/80 text-white' };
  }
  if (normalized.includes('trend') || normalized.includes('up')) {
    return { label: '🟢 Trending Up', className: 'bg-emerald-600/80 text-white' };
  }
  return { label: '🟡 Ranging', className: 'bg-yellow-600/80 text-white' };
}

function isPreMarket(now: Date): boolean {
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const day = ist.getDay();
  const totalMin = ist.getHours() * 60 + ist.getMinutes();
  return day >= 1 && day <= 5 && totalMin >= 525 && totalMin <= 555;
}

function confidenceClass(confidencePct: number): string {
  if (confidencePct > HIGH_CONFIDENCE_THRESHOLD) return 'bg-emerald-500';
  if (confidencePct >= MEDIUM_CONFIDENCE_THRESHOLD) return 'bg-yellow-400';
  return 'bg-red-500';
}

export default function PredictionChart() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const zoneSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const lastCandleTimeRef = useRef<number | null>(null);
  const [now, setNow] = useState(() => new Date());

  const { candles, loading, error } = useIntradayCandles(50);
  const { data: prediction } = useLivePrediction(30_000);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), CLOCK_UPDATE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const preMarket = useMemo(() => isPreMarket(now), [now]);
  const lastCandle = candles.length > 0 ? candles[candles.length - 1] : null;
  const predictionZone = useMemo(
    () => buildPredictionZone(lastCandle, prediction),
    [lastCandle, prediction],
  );

  const confidencePct = Math.round((predictionZone?.confidence ?? 0) * 100);
  const regimeBadge = getRegimeBadge(predictionZone?.regime ?? 'ranging');

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: CHART_HEIGHT,
      layout: {
        background: { color: '#0A0F1E' },
        textColor: '#D6E0F0',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      },
      grid: {
        vertLines: { color: '#1E293B' },
        horzLines: { color: '#1E293B' },
      },
      crosshair: {
        vertLine: { visible: true },
        horzLine: { visible: true },
      },
      timeScale: {
        borderColor: '#1E293B',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#1E293B',
      },
      localization: {
        locale: 'en-IN',
        timeFormatter: (time: UTCTimestamp) => {
          const date = new Date(Number(time) * 1000);
          return date.toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            hour: '2-digit',
            minute: '2-digit',
            day: '2-digit',
            month: 'short',
            hour12: false,
          });
        },
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22C55E',
      downColor: '#EF4444',
      wickUpColor: '#22C55E',
      wickDownColor: '#EF4444',
      borderUpColor: '#22C55E',
      borderDownColor: '#EF4444',
      priceLineVisible: false,
    });

    const zoneSeries = chart.addSeries(LineSeries, {
      color: '#94A3B8',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    zoneSeriesRef.current = zoneSeries;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry || !chartRef.current) return;
      chartRef.current.applyOptions({ width: entry.contentRect.width });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      zoneSeriesRef.current = null;
      lastCandleTimeRef.current = null;
    };
  }, []);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    if (!candleSeries || candles.length === 0) return;

    const lastRenderedTime = lastCandleTimeRef.current;
    if (lastRenderedTime === null) {
      candleSeries.setData(candles.map(toChartCandle));
      lastCandleTimeRef.current = candles[candles.length - 1].time;
      chartRef.current?.timeScale().fitContent();
      return;
    }

    const updates = candles.filter((candle) => candle.time >= lastRenderedTime);
    if (updates.length === 0) return;

    for (const candle of updates) {
      candleSeries.update(toChartCandle(candle));
    }
    lastCandleTimeRef.current = candles[candles.length - 1].time;
  }, [candles]);

  useEffect(() => {
    const zoneSeries = zoneSeriesRef.current;
    if (!zoneSeries || !lastCandle || !predictionZone) return;

    const movePct = prediction?.predicted_move_pct ?? 0;
    const direction = predictionZone.direction;
    const targetPrice =
      direction === 'HOLD'
        ? lastCandle.close
        : movePct !== 0
          ? lastCandle.close * (1 + movePct / 100)
          : direction === 'BUY'
            ? lastCandle.close * 1.001
            : lastCandle.close * 0.999;

    const color = direction === 'BUY' ? '#22C55E' : direction === 'SELL' ? '#EF4444' : '#94A3B8';
    zoneSeries.applyOptions({ color, lineStyle: LineStyle.Dashed });

    const zoneData: LineData<UTCTimestamp>[] = [
      { time: toUtcTimestamp(lastCandle.time), value: lastCandle.close },
      { time: toUtcTimestamp(predictionZone.target_time), value: targetPrice },
    ];
    zoneSeries.setData(zoneData);
  }, [lastCandle, prediction, predictionZone]);

  return (
    <section className="w-full h-[480px] rounded-xl border border-[#1E293B] bg-[#0A0F1E] p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm uppercase tracking-[0.18em] text-mist font-semibold">
          Live Prediction Chart
        </h2>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${regimeBadge.className}`}>
          {regimeBadge.label}
        </span>
      </div>

      {preMarket && (
        <p className="text-xs text-yellow-300 mb-2">
          ⏳ Pre-market — using GIFT Nifty + global cues
        </p>
      )}

      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" style={{ height: `${CHART_HEIGHT}px` }} />

      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-ash mb-1">
          <span>Prediction Confidence: {confidencePct}%</span>
          <span className="font-mono">{loading ? 'Loading...' : error ? 'Feed Error' : 'Live'}</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-deep/80 overflow-hidden">
          <div
            className={`h-full ${confidenceClass(confidencePct)} transition-all duration-500 ease-out`}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>
    </section>
  );
}
