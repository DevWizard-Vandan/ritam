import { useAccuracy } from '../hooks';
import type { SignalByType } from '../types';

/* ── Accuracy bar sub-component ── */
function AccuracyBar({
  label,
  stats,
  color,
}: {
  label: string;
  stats: SignalByType;
  color: string;
}) {
  const pct = stats.accuracy_pct * 100;
  const colorMap: Record<string, { bar: string; text: string; bg: string }> = {
    buy: {
      bar: 'bg-signal-buy',
      text: 'text-signal-buy',
      bg: 'bg-signal-buy-dim',
    },
    sell: {
      bar: 'bg-signal-sell',
      text: 'text-signal-sell',
      bg: 'bg-signal-sell-dim',
    },
    hold: {
      bar: 'bg-signal-hold',
      text: 'text-signal-hold',
      bg: 'bg-signal-hold-dim',
    },
  };
  const c = colorMap[color] || colorMap.hold;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-mist">
          {label}
        </span>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${c.text}`}>{pct.toFixed(1)}%</span>
          <span className="text-[11px] text-ash">
            {stats.correct}/{stats.total}
          </span>
        </div>
      </div>
      <div className={`w-full h-2 rounded-full ${c.bg} overflow-hidden`}>
        <div
          className={`h-full rounded-full ${c.bar} transition-all duration-700 ease-out`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

/* ── Skeleton loader ── */
function SkeletonBar() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="flex justify-between">
        <div className="h-3 w-12 rounded bg-steel/40" />
        <div className="h-3 w-16 rounded bg-steel/40" />
      </div>
      <div className="h-2 w-full rounded-full bg-steel/30" />
    </div>
  );
}

export default function AccuracyPanel() {
  const { data, loading, error } = useAccuracy(60_000);

  const overallPct = data ? (data.accuracy_pct * 100).toFixed(1) : '0.0';
  const total = data?.total ?? 0;

  return (
    <div id="accuracy-panel" className="glass-card p-6 sm:p-7 flex flex-col gap-5 animate-slide-up" style={{ animationDelay: '0.1s' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-mist">
          Prediction Accuracy
        </h3>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${error ? 'bg-signal-sell' : 'bg-signal-buy'} animate-pulse-slow`} />
          <span className="text-[10px] text-ash uppercase tracking-wider">
            {error ? 'Offline' : 'Live'}
          </span>
        </div>
      </div>

      {/* Large accuracy readout */}
      <div className="flex items-end gap-2">
        <span className="text-4xl sm:text-5xl font-black text-frost tabular-nums leading-none">
          {loading ? '—' : overallPct}
        </span>
        <span className="text-lg font-medium text-ash mb-0.5">%</span>
      </div>

      <div className="flex items-center gap-3 text-xs text-ash">
        <span>{total} resolved prediction{total !== 1 ? 's' : ''}</span>
        {data && data.avg_error > 0 && (
          <>
            <span className="w-px h-3 bg-steel" />
            <span>Avg error: {(data.avg_error).toFixed(4)}%</span>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-steel to-transparent" />

      {/* Per-signal breakdown */}
      <div className="space-y-4">
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
          <p className="text-sm text-ash text-center py-4">No accuracy data available yet.</p>
        )}
      </div>
    </div>
  );
}
