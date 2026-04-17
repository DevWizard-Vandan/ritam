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
import type { CandleData, ScenarioResult } from '../types';

const CHART_HEIGHT = 390;
const NARRATIVE_ANIMATION_DELAY_MS = 300;
const CANDLE_STEP_DELAY_MS = 400;

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

type SandboxChartProps = {
  result: ScenarioResult | null;
};

export default function SandboxChart({ result }: SandboxChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const historicalSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const projectedSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const boundarySeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const [showNarrativeOverlay, setShowNarrativeOverlay] = useState(false);

  const projectedColor = useMemo(
    () => getProjectedColor(result?.regime ?? 'buy'),
    [result?.regime],
  );

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
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          });
        },
      },
    });

    const historicalSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#64748B80',
      downColor: '#64748B80',
      wickUpColor: '#64748B80',
      wickDownColor: '#64748B80',
      borderUpColor: '#64748B80',
      borderDownColor: '#64748B80',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const projectedSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22C55E',
      downColor: '#22C55E',
      wickUpColor: '#22C55E',
      wickDownColor: '#22C55E',
      borderUpColor: '#22C55E',
      borderDownColor: '#22C55E',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const boundarySeries = chart.addSeries(LineSeries, {
      color: '#94A3B8',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    chartRef.current = chart;
    historicalSeriesRef.current = historicalSeries;
    projectedSeriesRef.current = projectedSeries;
    boundarySeriesRef.current = boundarySeries;

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
      historicalSeriesRef.current = null;
      projectedSeriesRef.current = null;
      boundarySeriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const historicalSeries = historicalSeriesRef.current;
    const projectedSeries = projectedSeriesRef.current;
    const boundarySeries = boundarySeriesRef.current;

    if (!historicalSeries || !projectedSeries || !boundarySeries) return;

    setShowNarrativeOverlay(false);
    projectedSeries.applyOptions({
      upColor: projectedColor,
      downColor: projectedColor,
      wickUpColor: projectedColor,
      wickDownColor: projectedColor,
      borderUpColor: projectedColor,
      borderDownColor: projectedColor,
    });

    if (!result) {
      historicalSeries.setData([]);
      projectedSeries.setData([]);
      boundarySeries.setData([]);
      return;
    }

    const historicalData = result.historical_candles.map(toChartCandle);
    historicalSeries.setData(historicalData);
    projectedSeries.setData([]);

    const boundaryCandle = result.historical_candles[result.historical_candles.length - 1];
    if (boundaryCandle) {
      const projected = result.projected_candles;
      const projectedHigh = projected.length > 0 ? Math.max(...projected.map((c) => c.high)) : boundaryCandle.high;
      const projectedLow = projected.length > 0 ? Math.min(...projected.map((c) => c.low)) : boundaryCandle.low;
      const lineData: LineData<UTCTimestamp>[] = [
        { time: toUtcTimestamp(boundaryCandle.time), value: projectedLow },
        { time: toUtcTimestamp(boundaryCandle.time), value: projectedHigh },
      ];
      boundarySeries.setData(lineData);
    } else {
      boundarySeries.setData([]);
    }

    chartRef.current?.timeScale().fitContent();

    const timers: ReturnType<typeof setTimeout>[] = [];
    timers.push(
      setTimeout(() => {
        const animatedData: CandlestickData<UTCTimestamp>[] = [];

        result.projected_candles.forEach((candle, index) => {
          timers.push(
            setTimeout(() => {
              animatedData.push(toChartCandle(candle));
              projectedSeries.setData(animatedData);

              if (index === result.projected_candles.length - 1) {
                setShowNarrativeOverlay(true);
              }
            }, index * CANDLE_STEP_DELAY_MS),
          );
        });

        if (result.projected_candles.length === 0) {
          setShowNarrativeOverlay(true);
        }
      }, NARRATIVE_ANIMATION_DELAY_MS),
    );

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [projectedColor, result]);

  return (
    <div className="relative w-full">
      <div
        ref={containerRef}
        className="w-full rounded-lg overflow-hidden border border-[#1E293B]"
        style={{ height: `${CHART_HEIGHT}px` }}
      />

      {result && (
        <span className="absolute top-3 right-3 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-slate-900/80 text-slate-100 border border-slate-600/60">
          {getSourceBadge(result.data_source)}
        </span>
      )}

      {result && showNarrativeOverlay && (
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
