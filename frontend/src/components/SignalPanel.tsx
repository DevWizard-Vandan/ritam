import { motion } from 'framer-motion';
import { useLivePrediction } from '../hooks';
import type { PredictionData } from '../types';

const MOCK_SIGNAL: PredictionData = {
  timestamp: new Date().toISOString(),
  predicted_direction: 'hold',
  predicted_move_pct: 0,
  confidence: 0,
  timeframe_minutes: 20,
  regime: 'awaiting_data',
};

function getSignalConfig(direction: string) {
  switch (direction.toLowerCase()) {
    case 'up':
    case 'buy':
      return {
        label: 'BUY',
        textClass: 'text-green-700',
        badgeClass: 'border border-green-200 bg-green-50 text-green-700',
        dotClass: 'bg-green-600',
      };
    case 'down':
    case 'sell':
      return {
        label: 'SELL',
        textClass: 'text-red-700',
        badgeClass: 'border border-red-200 bg-red-50 text-red-700',
        dotClass: 'bg-red-600',
      };
    default:
      return {
        label: 'HOLD',
        textClass: 'text-amber-700',
        badgeClass: 'border border-amber-200 bg-amber-50 text-amber-700',
        dotClass: 'bg-amber-600',
      };
  }
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString('en-IN', {
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
  const { data, loading, connected } = useLivePrediction(30_000);
  const signal = data ?? MOCK_SIGNAL;
  const cfg = getSignalConfig(signal.predicted_direction);
  const confidencePct = Math.round(signal.confidence <= 1 ? signal.confidence * 100 : signal.confidence);
  const signalKey = `${signal.timestamp}-${cfg.label}`;

  return (
    <motion.section
      id="signal-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="panel-label">Current Signal</p>
            <p className="panel-value mt-3">
              {loading ? '--' : `${signal.predicted_move_pct >= 0 ? '+' : ''}${signal.predicted_move_pct.toFixed(2)}%`}
            </p>
            <p className="mt-2 text-sm font-normal text-slate-600">
              15-minute market stance with live prediction wiring intact.
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
            <span className={`h-2 w-2 rounded-full ${connected ? 'bg-green-500' : 'bg-slate-300'}`} />
            <span>{loading ? 'Loading' : connected ? 'WebSocket' : 'REST Fallback'}</span>
          </div>
        </div>

        <motion.div
          key={signalKey}
          animate={{ scale: [1, 1.08, 1] }}
          transition={{ duration: 0.3 }}
          className={`inline-flex w-fit items-center gap-3 rounded-full px-4 py-2 text-sm font-semibold ${cfg.badgeClass}`}
        >
          <span className={`h-2.5 w-2.5 rounded-full ${cfg.dotClass}`} />
          <span className={cfg.textClass}>{loading ? 'Awaiting data' : cfg.label}</span>
        </motion.div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="panel-muted p-4">
            <p className="panel-label">Confidence</p>
            <p className="mt-3 font-mono text-2xl font-semibold text-slate-900">
              {loading ? '--' : `${confidencePct}%`}
            </p>
          </div>
          <div className="panel-muted p-4">
            <p className="panel-label">Regime</p>
            <p className="mt-3 text-lg font-semibold capitalize text-slate-900">
              {loading ? '--' : signal.regime.replaceAll('_', ' ')}
            </p>
          </div>
          <div className="panel-muted p-4">
            <p className="panel-label">Window</p>
            <p className="mt-3 font-mono text-2xl font-semibold text-slate-900">
              {signal.timeframe_minutes}m
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 border-t border-slate-200 pt-4 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <span>Signal direction: <span className={`font-semibold ${cfg.textClass}`}>{cfg.label}</span></span>
          <span className="font-mono text-slate-500">
            {loading ? 'Waiting for prediction feed' : `Updated ${formatTimestamp(signal.timestamp)}`}
          </span>
        </div>
      </div>
    </motion.section>
  );
}
