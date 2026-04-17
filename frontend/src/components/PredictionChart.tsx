import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useIntradayCandles, useLivePrediction } from '../hooks';
import type { CandleData, PredictionData, PredictionZone } from '../types';

const CHART_HEIGHT = 390;
const CLOCK_UPDATE_INTERVAL_MS = 30_000;

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
    return {
      label: 'Crisis',
      className: 'border border-red-200 bg-red-50 text-red-700',
    };
  }
  if (normalized.includes('trend') || normalized.includes('up')) {
    return {
      label: 'Trending Up',
      className: 'border border-green-200 bg-green-50 text-green-700',
    };
  }
  return {
    label: 'Ranging',
    className: 'border border-amber-200 bg-amber-50 text-amber-700',
  };
}

function isPreMarket(now: Date): boolean {
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const day = ist.getDay();
  const totalMin = ist.getHours() * 60 + ist.getMinutes();
  return day >= 1 && day <= 5 && totalMin >= 525 && totalMin <= 555;
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
  const lastCandleX = candles.length > 0 ? 12 + (candles.length - 0.5) * candleGap : 12;
  const lastCloseY = lastCandle ? scaleY(lastCandle.close, yScale.min, yScale.max, CHART_HEIGHT) : CHART_HEIGHT / 2;
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

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="panel-label">Live Prediction Chart</p>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <p className="panel-value">
                {lastCandle ? lastCandle.close.toFixed(2) : '--'}
              </p>
              <p className="pb-1 font-mono text-sm text-slate-500">
                {predictionZone ? `${predictionZone.direction} ${movePct >= 0 ? '+' : ''}${movePct.toFixed(2)}%` : 'Awaiting prediction'}
              </p>
            </div>
            <p className="mt-2 text-sm text-slate-600">
              Intraday Nifty structure with a 15-minute projection overlay.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {preMarket && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700">
                Pre-market cues active
              </span>
            )}
            <span className={`rounded-full px-3 py-1.5 text-xs font-medium ${regimeBadge.className}`}>
              {regimeBadge.label}
            </span>
          </div>
        </div>

        <div
          ref={chartRef}
          className="overflow-hidden rounded-xl border border-slate-200 bg-white"
          style={{ height: `${CHART_HEIGHT}px` }}
        >
          <svg width="100%" height={CHART_HEIGHT} viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`} preserveAspectRatio="none">
            <rect x={0} y={0} width={chartWidth} height={CHART_HEIGHT} fill="#FFFFFF" />
            {[0.2, 0.4, 0.6, 0.8].map((ratio) => (
              <line
                key={ratio}
                x1={0}
                y1={CHART_HEIGHT * ratio}
                x2={chartWidth}
                y2={CHART_HEIGHT * ratio}
                stroke="#F1F5F9"
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
              const color = isUp ? '#16A34A' : '#DC2626';
              return (
                <g key={candle.time}>
                  <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth={1.2} />
                  <rect
                    x={x - candleBodyWidth / 2}
                    y={Math.min(openY, closeY)}
                    width={candleBodyWidth}
                    height={Math.max(1.5, Math.abs(closeY - openY))}
                    fill={color}
                    rx={1}
                  />
                </g>
              );
            })}

            {lastCandle && (
              <>
                <line
                  x1={lastCandleX}
                  y1={0}
                  x2={lastCandleX}
                  y2={CHART_HEIGHT}
                  stroke="#94A3B8"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                />
                <line
                  x1={0}
                  y1={lastCloseY}
                  x2={chartWidth}
                  y2={lastCloseY}
                  stroke="#94A3B8"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                />
              </>
            )}

            {lastCandle && predictionZone && targetPrice !== null && (
              <>
                <line
                  x1={lastCandleX}
                  y1={lastCloseY}
                  x2={Math.min(chartWidth - 8, 12 + (candles.length + 2.5) * candleGap)}
                  y2={scaleY(targetPrice, yScale.min, yScale.max, CHART_HEIGHT)}
                  stroke="#3B82F6"
                  strokeWidth={2}
                  strokeDasharray="6 5"
                />
                <circle
                  cx={Math.min(chartWidth - 8, 12 + (candles.length + 2.5) * candleGap)}
                  cy={scaleY(targetPrice, yScale.min, yScale.max, CHART_HEIGHT)}
                  r={4}
                  fill="#3B82F6"
                />
              </>
            )}
          </svg>
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600">
            <span>Prediction confidence</span>
            <span className="font-mono text-slate-900">
              {loading ? 'Loading...' : error ? 'Feed error' : `${confidencePct}%`}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${confidencePct}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
              className="h-full rounded-full bg-blue-500"
            />
          </div>
        </div>
      </div>
    </motion.section>
  );
}
