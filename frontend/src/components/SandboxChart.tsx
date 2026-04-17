import { useEffect, useMemo, useRef, useState } from 'react';
import type { CandleData, ScenarioResult } from '../types';

const CHART_HEIGHT = 390;
const NARRATIVE_ANIMATION_DELAY_MS = 300;
const CANDLE_STEP_DELAY_MS = 400;

function getProjectedColor(regime: string): string {
  const normalized = regime.toLowerCase();
  if (normalized.includes('sell') || normalized.includes('crisis') || normalized.includes('down')) {
    return '#EF4444';
  }
  if (normalized.includes('range')) {
    return '#EAB308';
  }
  return '#22C55E';
}

function getSourceBadge(source: ScenarioResult['data_source']): string {
  if (source === 'db') return '📦 DB';
  if (source === 'yfinance') return '📈 yfinance';
  return '🧠 Gemini';
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

type SandboxChartProps = {
  result: ScenarioResult | null;
};

export default function SandboxChart({ result }: SandboxChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [chartWidth, setChartWidth] = useState(900);
  const [animationState, setAnimationState] = useState<{ key: string | null; count: number; completed: boolean }>({
    key: null,
    count: 0,
    completed: false,
  });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setChartWidth(Math.max(320, Math.floor(entry.contentRect.width)));
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const scenarioKey = useMemo(() => {
    if (!result) return null;
    return [
      result.date,
      result.condition ?? '',
      result.regime,
      String(result.projected_candles.length),
      result.narrative,
    ].join('|');
  }, [result]);

  useEffect(() => {
    if (!result || !scenarioKey) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    timers.push(
      setTimeout(() => {
        setAnimationState({ key: scenarioKey, count: 0, completed: false });

        result.projected_candles.forEach((_, index) => {
          timers.push(
            setTimeout(() => {
              const count = index + 1;
              setAnimationState({
                key: scenarioKey,
                count,
                completed: count === result.projected_candles.length,
              });
            }, index * CANDLE_STEP_DELAY_MS),
          );
        });

        if (result.projected_candles.length === 0) {
          setAnimationState({ key: scenarioKey, count: 0, completed: true });
        }
      }, NARRATIVE_ANIMATION_DELAY_MS),
    );

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [result, scenarioKey]);

  const historicalCandles = result?.historical_candles ?? [];
  const visibleProjectedCount = animationState.key === scenarioKey ? animationState.count : 0;
  const visibleProjectedCandles = (result?.projected_candles ?? []).slice(0, visibleProjectedCount);
  const allVisibleCandles = [...historicalCandles, ...visibleProjectedCandles];
  const yScale = createYScale(allVisibleCandles.length > 0 ? allVisibleCandles : historicalCandles);
  const totalCandles = Math.max(1, historicalCandles.length + Math.max(result?.projected_candles.length ?? 0, 1));
  const candleGap = (chartWidth - 24) / totalCandles;
  const candleBodyWidth = Math.max(2, Math.floor(candleGap * 0.55));
  const projectedColor = getProjectedColor(result?.regime ?? 'buy');

  return (
    <div className="relative w-full">
      <div
        ref={containerRef}
        className="w-full rounded-lg overflow-hidden border border-[#1E293B]"
        style={{ height: `${CHART_HEIGHT}px` }}
      >
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

          {historicalCandles.map((candle, index) => {
            const x = 12 + index * candleGap + candleGap / 2;
            const openY = scaleY(candle.open, yScale.min, yScale.max, CHART_HEIGHT);
            const closeY = scaleY(candle.close, yScale.min, yScale.max, CHART_HEIGHT);
            const highY = scaleY(candle.high, yScale.min, yScale.max, CHART_HEIGHT);
            const lowY = scaleY(candle.low, yScale.min, yScale.max, CHART_HEIGHT);
            const color = '#64748B';
            return (
              <g key={`hist-${candle.time}`} opacity={0.5}>
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

          {historicalCandles.length > 0 && (
            <line
              x1={12 + (historicalCandles.length - 0.5) * candleGap}
              y1={0}
              x2={12 + (historicalCandles.length - 0.5) * candleGap}
              y2={CHART_HEIGHT}
              stroke="#94A3B8"
              strokeWidth={1.5}
              strokeDasharray="5 5"
            />
          )}

          {visibleProjectedCandles.map((candle, index) => {
            const absoluteIndex = historicalCandles.length + index;
            const x = 12 + absoluteIndex * candleGap + candleGap / 2;
            const openY = scaleY(candle.open, yScale.min, yScale.max, CHART_HEIGHT);
            const closeY = scaleY(candle.close, yScale.min, yScale.max, CHART_HEIGHT);
            const highY = scaleY(candle.high, yScale.min, yScale.max, CHART_HEIGHT);
            const lowY = scaleY(candle.low, yScale.min, yScale.max, CHART_HEIGHT);
            return (
              <g key={`proj-${candle.time}`}>
                <line x1={x} y1={highY} x2={x} y2={lowY} stroke={projectedColor} strokeWidth={1.2} />
                <rect
                  x={x - candleBodyWidth / 2}
                  y={Math.min(openY, closeY)}
                  width={candleBodyWidth}
                  height={Math.max(1.5, Math.abs(closeY - openY))}
                  fill={projectedColor}
                  rx={1}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {result && (
        <span className="absolute top-3 right-3 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-slate-900/80 text-slate-100 border border-slate-600/60">
          {getSourceBadge(result.data_source)}
        </span>
      )}

      {result && scenarioKey && animationState.key === scenarioKey && animationState.completed && (
        <div className="absolute left-3 bottom-3 max-w-[70%] rounded-md bg-slate-950/80 border border-slate-700/70 px-3 py-2 text-xs text-white leading-relaxed">
          <p
            style={{
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {result.narrative}
          </p>
        </div>
      )}
    </div>
  );
}
