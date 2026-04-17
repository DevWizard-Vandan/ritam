import { motion } from 'framer-motion';
import { useAccuracy } from '../hooks';
import type { SignalByType } from '../types';

function AccuracyBar({
  label,
  stats,
  color,
}: {
  label: string;
  stats: SignalByType;
  color: 'buy' | 'sell' | 'hold';
}) {
  const pct = stats.accuracy_pct * 100;
  const colorMap: Record<'buy' | 'sell' | 'hold', string> = {
    buy: 'bg-green-600',
    sell: 'bg-red-600',
    hold: 'bg-amber-600',
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="panel-label">{label}</span>
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-semibold text-slate-900">{pct.toFixed(1)}%</span>
          <span className="font-mono text-xs text-slate-500">
            {stats.correct}/{stats.total}
          </span>
        </div>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(pct, 100)}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={`h-full rounded-full ${colorMap[color]}`}
        />
      </div>
    </div>
  );
}

function SkeletonBar() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="flex justify-between">
        <div className="h-3 w-16 rounded bg-slate-200" />
        <div className="h-3 w-20 rounded bg-slate-200" />
      </div>
      <div className="h-2 rounded-full bg-slate-100" />
    </div>
  );
}

export default function AccuracyPanel() {
  const { data, loading, error } = useAccuracy(60_000);
  const overallPct = data ? (data.accuracy_pct * 100).toFixed(1) : '--';

  return (
    <motion.section
      id="accuracy-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="panel-label">Prediction Accuracy</p>
            <p className="panel-value mt-3">{overallPct}%</p>
            <p className="mt-2 text-sm text-slate-600">
              Resolved outcomes versus recent predictions.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
            <span className={`h-2 w-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'}`} />
            <span>{error ? 'Offline' : 'Live'}</span>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="panel-muted p-4">
            <p className="panel-label">Resolved</p>
            <p className="mt-3 font-mono text-2xl font-semibold text-slate-900">{data?.total ?? 0}</p>
          </div>
          <div className="panel-muted p-4">
            <p className="panel-label">Correct</p>
            <p className="mt-3 font-mono text-2xl font-semibold text-slate-900">{data?.correct ?? 0}</p>
          </div>
          <div className="panel-muted p-4">
            <p className="panel-label">Avg Error</p>
            <p className="mt-3 font-mono text-2xl font-semibold text-slate-900">
              {data ? `${data.avg_error.toFixed(4)}%` : '--'}
            </p>
          </div>
        </div>

        <div className="space-y-4 border-t border-slate-200 pt-4">
          {loading ? (
            <>
              <SkeletonBar />
              <SkeletonBar />
              <SkeletonBar />
            </>
          ) : data ? (
            <>
              <AccuracyBar label="Buy" stats={data.by_signal.buy} color="buy" />
              <AccuracyBar label="Sell" stats={data.by_signal.sell} color="sell" />
              <AccuracyBar label="Hold" stats={data.by_signal.hold} color="hold" />
            </>
          ) : (
            <p className="text-sm text-slate-500">No accuracy data available yet.</p>
          )}
        </div>
      </div>
    </motion.section>
  );
}
