import { useEffect, useMemo, useRef, useState } from 'react';
import { useIntradayCandles, useLivePrediction } from '../hooks';
import type { CandleData, PredictionData, PredictionZone } from '../types';

const CHART_HEIGHT = 390;
const CLOCK_UPDATE_INTERVAL_MS = 30_000;
const HIGH_CONFIDENCE_THRESHOLD = 70;
const MEDIUM_CONFIDENCE_THRESHOLD = 40;

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

function createYScale(candles: CandleData[], padding = 0.05): { min: number; max: number } {
  if (candles.length === 0) return { min: 0, max: 1 };
  const low = Math.min(...candles.map((candle) => candle.low));
  const high = Math.max(...candles.map((candle) => candle.high));
  const span = Math.max(high - low, 1e-6);
  return {
    min: low - span * padding,
    max: high + span * padding,
  };
}

function scaleY(value: number, min: number, max: number, height: number): number {
  const ratio = (value - min) / (max - min);
  return height - ratio * height;
}

export default function PredictionChart() {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const [chartWidth, setChartWidth] = useState(900);
  const [now, setNow] = useState(() => new Date());

  const { candles, loading, error } = useIntradayCandles(50);
  const { data: prediction } = useLivePrediction(30_000);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), CLOCK_UPDATE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setChartWidth(Math.max(320, Math.floor(entry.contentRect.width)));
    });
    observer.observe(chartRef.current);
    return () => observer.disconnect();
  }, []);

  const preMarket = useMemo(() => isPreMarket(now), [now]);
  const lastCandle = candles.length > 0 ? candles[candles.length - 1] : null;
  const predictionZone = useMemo(
    () => buildPredictionZone(lastCandle, prediction),
    [lastCandle, prediction],
  );

  const confidencePct = Math.round((predictionZone?.confidence ?? 0) * 100);
  const regimeBadge = getRegimeBadge(predictionZone?.regime ?? 'ranging');
  const yScale = createYScale(candles);
  const candleGap = candles.length > 1 ? (chartWidth - 24) / candles.length : chartWidth - 24;
  const candleBodyWidth = Math.max(2, Math.floor(candleGap * 0.55));

  const movePct = prediction?.predicted_move_pct ?? 0;
  const targetPrice =
    !lastCandle || !predictionZone
      ? null
      : predictionZone.direction === 'HOLD'
        ? lastCandle.close
        : movePct !== 0
          ? lastCandle.close * (1 + movePct / 100)
          : predictionZone.direction === 'BUY'
            ? lastCandle.close * 1.001
            : lastCandle.close * 0.999;

  const zoneColor =
    predictionZone?.direction === 'BUY'
      ? '#22C55E'
      : predictionZone?.direction === 'SELL'
        ? '#EF4444'
        : '#94A3B8';

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

      <div ref={chartRef} className="w-full rounded-lg overflow-hidden border border-[#1E293B]" style={{ height: `${CHART_HEIGHT}px` }}>
        <svg width="100%" height={CHART_HEIGHT} viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`} preserveAspectRatio="none">
          <rect x={0} y={0} width={chartWidth} height={CHART_HEIGHT} fill="#0A0F1E" />
          {[0.2, 0.4, 0.6, 0.8].map((ratio) => (
            <line
              key={ratio}
              x1={0}
              y1={CHART_HEIGHT * ratio}
              x2={chartWidth}
              y2={CHART_HEIGHT * ratio}
              stroke="#1E293B"
              strokeWidth={1}
            />
          ))}

          {candles.map((candle, index) => {
            const x = 12 + index * candleGap + candleGap / 2;
            const openY = scaleY(candle.open, yScale.min, yScale.max, CHART_HEIGHT);
            const closeY = scaleY(candle.close, yScale.min, yScale.max, CHART_HEIGHT);
            const highY = scaleY(candle.high, yScale.min, yScale.max, CHART_HEIGHT);
            const lowY = scaleY(candle.low, yScale.min, yScale.max, CHART_HEIGHT);
            const isUp = candle.close >= candle.open;
            const color = isUp ? '#22C55E' : '#EF4444';
            return (
              <g key={candle.time}>
                <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth={1.2} />
                <rect
                  x={x - candleBodyWidth / 2}
                  y={Math.min(openY, closeY)}
                  width={candleBodyWidth}
                  height={Math.max(1.5, Math.abs(closeY - openY))}
                  fill={color}
                  opacity={0.95}
                  rx={1}
                />
              </g>
            );
          })}

          {lastCandle && predictionZone && targetPrice !== null && (
            <line
              x1={12 + (candles.length - 0.5) * candleGap}
              y1={scaleY(lastCandle.close, yScale.min, yScale.max, CHART_HEIGHT)}
              x2={Math.min(chartWidth - 8, 12 + (candles.length + 2.5) * candleGap)}
              y2={scaleY(targetPrice, yScale.min, yScale.max, CHART_HEIGHT)}
              stroke={zoneColor}
              strokeWidth={2}
              strokeDasharray="6 5"
            />
          )}
        </svg>
      </div>

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
