import { useCandles } from '../hooks';
import type { PredictionData } from '../types';

/* ── Mock signal data when backend is not available ── */
const MOCK_SIGNAL: PredictionData = {
  timestamp: new Date().toISOString(),
  predicted_direction: 'hold',
  predicted_move_pct: 0.0,
  confidence: 0.0,
  timeframe_minutes: 20,
  regime: 'awaiting_data',
};

function getSignalConfig(direction: string) {
  switch (direction.toLowerCase()) {
    case 'up':
    case 'buy':
      return {
        label: 'BUY',
        textClass: 'text-signal-buy',
        glowClass: 'glow-buy',
        bgGradient: 'from-signal-buy-glow via-transparent to-transparent',
        dotColor: 'bg-signal-buy',
        ringColor: 'ring-signal-buy/30',
      };
    case 'down':
    case 'sell':
      return {
        label: 'SELL',
        textClass: 'text-signal-sell',
        glowClass: 'glow-sell',
        bgGradient: 'from-signal-sell-glow via-transparent to-transparent',
        dotColor: 'bg-signal-sell',
        ringColor: 'ring-signal-sell/30',
      };
    default:
      return {
        label: 'HOLD',
        textClass: 'text-signal-hold',
        glowClass: 'glow-hold',
        bgGradient: 'from-signal-hold-glow via-transparent to-transparent',
        dotColor: 'bg-signal-hold',
        ringColor: 'ring-signal-hold/30',
      };
  }
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return ts;
  }
}

export default function SignalPanel() {
  const { data: candlesData, loading } = useCandles(1, 60_000);

  /* Derive signal from latest candle's price movement for now */
  const signal: PredictionData = (() => {
    if (!candlesData || candlesData.candles.length === 0) return MOCK_SIGNAL;
    const latest = candlesData.candles[candlesData.candles.length - 1];
    const pctChange = latest.close && latest.open
      ? ((latest.close - latest.open) / latest.open) * 100
      : 0;
    const direction = pctChange > 0.05 ? 'buy' : pctChange < -0.05 ? 'sell' : 'hold';
    return {
      timestamp: latest.timestamp_ist || new Date().toISOString(),
      predicted_direction: direction,
      predicted_move_pct: Math.abs(pctChange),
      confidence: Math.min(0.95, 0.5 + Math.abs(pctChange) * 10),
      timeframe_minutes: 20,
      regime: Math.abs(pctChange) > 0.5 ? 'event_driven' : 'baseline',
    };
  })();

  const cfg = getSignalConfig(signal.predicted_direction);
  const sentimentScore = signal.confidence;

  return (
    <div
      id="signal-panel"
      className={`glass-card ${cfg.glowClass} animate-glow-breathe relative overflow-hidden p-6 sm:p-8 flex flex-col items-center justify-center gap-5`}
    >
      {/* Background radial glow */}
      <div
        className={`absolute inset-0 bg-gradient-radial ${cfg.bgGradient} opacity-40 pointer-events-none`}
      />

      {/* Header */}
      <div className="relative z-10 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-mist">
        <span className={`w-2 h-2 rounded-full ${cfg.dotColor} animate-pulse-slow`} />
        Live Signal
      </div>

      {/* Main signal */}
      <div className="relative z-10 flex flex-col items-center gap-2">
        <h2
          className={`text-5xl sm:text-6xl lg:text-7xl font-black tracking-tight ${cfg.textClass} transition-all duration-500`}
        >
          {loading ? '—' : cfg.label}
        </h2>
        <p className="text-sm text-mist font-medium">
          {loading ? 'Loading...' : `${(signal.predicted_move_pct).toFixed(2)}% expected move`}
        </p>
      </div>

      {/* Badges row */}
      <div className="relative z-10 flex flex-wrap items-center justify-center gap-3 mt-1">
        {/* Confidence */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-deep/70 border border-steel/40">
          <span className="text-xs text-ash uppercase tracking-wider">Confidence</span>
          <span className={`text-sm font-semibold ${cfg.textClass}`}>
            {loading ? '—' : `${(sentimentScore * 100).toFixed(0)}%`}
          </span>
        </div>
        {/* Regime */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-deep/70 border border-steel/40">
          <span className="text-xs text-ash uppercase tracking-wider">Regime</span>
          <span className="text-sm font-semibold text-cyan">
            {loading ? '—' : signal.regime.replace('_', ' ')}
          </span>
        </div>
        {/* Timeframe */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-deep/70 border border-steel/40">
          <span className="text-xs text-ash uppercase tracking-wider">Window</span>
          <span className="text-sm font-semibold text-silver">
            {signal.timeframe_minutes}m
          </span>
        </div>
      </div>

      {/* Timestamp */}
      <p className="relative z-10 text-xs text-ash mt-1">
        {loading ? '' : `Last update: ${formatTimestamp(signal.timestamp)}`}
      </p>
    </div>
  );
}
