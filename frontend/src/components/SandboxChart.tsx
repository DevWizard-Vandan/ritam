import { useEffect, useMemo, useRef, useState } from 'react';
import type { CandleData, ScenarioResult } from '../types';

const CHART_HEIGHT = 390;
const NARRATIVE_ANIMATION_DELAY_MS = 300;
const CANDLE_STEP_DELAY_MS = 400;

function getProjectedColor(regime: string): string {
  const normalized = regime.toLowerCase();
  if (normalized.includes('sell') || normalized.includes('crisis') || normalized.includes('down')) {
    return '#DC2626';
  }
  if (normalized.includes('range')) {
    return '#D97706';
  }
  return '#16A34A';
}

function getSourceBadge(source: ScenarioResult['data_source']): string {
  if (source === 'db') return 'DB';
  if (source === 'yfinance') return 'yfinance';
  return 'Gemini';
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
  const [animationState, setAnimationState] = useState<{ key: string | null; count: number }>({
    key: null,
    count: 0,
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
        setAnimationState({ key: scenarioKey, count: 0 });

        result.projected_candles.forEach((_, index) => {
          timers.push(
            setTimeout(() => {
              setAnimationState({
                key: scenarioKey,
                count: index + 1,
              });
            }, index * CANDLE_STEP_DELAY_MS),
          );
        });

        if (result.projected_candles.length === 0) {
          setAnimationState({ key: scenarioKey, count: 0 });
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
  const historicalDividerX = historicalCandles.length > 0 ? 12 + (historicalCandles.length - 0.5) * candleGap : 12;

  return (
    <div className="relative w-full">
      <div
        ref={containerRef}
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

          {historicalCandles.map((candle, index) => {
            const x = 12 + index * candleGap + candleGap / 2;
            const openY = scaleY(candle.open, yScale.min, yScale.max, CHART_HEIGHT);
            const closeY = scaleY(candle.close, yScale.min, yScale.max, CHART_HEIGHT);
            const highY = scaleY(candle.high, yScale.min, yScale.max, CHART_HEIGHT);
            const lowY = scaleY(candle.low, yScale.min, yScale.max, CHART_HEIGHT);
            const isUp = candle.close >= candle.open;
            const color = isUp ? '#94A3B8' : '#CBD5E1';
            return (
              <g key={`hist-${candle.time}`}>
                <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth={1.1} />
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
              x1={historicalDividerX}
              y1={0}
              x2={historicalDividerX}
              y2={CHART_HEIGHT}
              stroke="#94A3B8"
              strokeWidth={1}
              strokeDasharray="4 4"
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
        <span className="absolute right-3 top-3 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-600 shadow-sm">
          {getSourceBadge(result.data_source)}
        </span>
      )}
    </div>
  );
}
