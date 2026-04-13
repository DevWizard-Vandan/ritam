import { useAnalogs } from '../hooks';
import type { Analog } from '../types';

/* ── Similarity visual indicator ── */
function SimilarityArc({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const circumference = 2 * Math.PI * 28;
  const offset = circumference - (score * circumference);

  return (
    <div className="relative w-16 h-16 flex-shrink-0">
      <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90">
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke="rgba(42,53,85,0.4)"
          strokeWidth="3"
        />
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke="url(#similarity-gradient)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
        <defs>
          <linearGradient id="similarity-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6c5ce7" />
            <stop offset="100%" stopColor="#00d4ff" />
          </linearGradient>
        </defs>
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-frost rotate-0">
        {pct}%
      </span>
    </div>
  );
}

/* ── Analog card ── */
function AnalogCard({ analog, index }: { analog: Analog; index: number }) {
  const isPositive = analog.next_5day_return >= 0;

  return (
    <div
      className="glass-card p-4 sm:p-5 flex items-center gap-4 group animate-slide-up"
      style={{ animationDelay: `${0.15 + index * 0.1}s` }}
    >
      <SimilarityArc score={analog.similarity_score} />

      <div className="flex-1 min-w-0 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wider text-ash">Period</span>
        </div>
        <p className="text-sm font-semibold text-frost truncate">
          {analog.start_date} → {analog.end_date}
        </p>
        <div className="flex items-center gap-3">
          <span className="text-xs text-ash">Next 5-day return:</span>
          <span
            className={`text-sm font-bold ${
              isPositive ? 'text-signal-buy' : 'text-signal-sell'
            }`}
          >
            {isPositive ? '+' : ''}{analog.next_5day_return.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Direction arrow */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isPositive ? 'bg-signal-buy-dim' : 'bg-signal-sell-dim'
        } transition-transform duration-300 group-hover:scale-110`}
      >
        <svg
          viewBox="0 0 16 16"
          className={`w-4 h-4 ${isPositive ? 'text-signal-buy' : 'text-signal-sell rotate-180'}`}
          fill="currentColor"
        >
          <path d="M8 3l5 6H3z" />
        </svg>
      </div>
    </div>
  );
}

/* ── Skeleton ── */
function SkeletonCard() {
  return (
    <div className="glass-card p-5 flex items-center gap-4 animate-pulse">
      <div className="w-16 h-16 rounded-full bg-steel/30 flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-16 rounded bg-steel/30" />
        <div className="h-4 w-40 rounded bg-steel/30" />
        <div className="h-3 w-24 rounded bg-steel/30" />
      </div>
    </div>
  );
}

/* ── Mock analogs for display when API is unavailable ── */
const MOCK_ANALOGS: Analog[] = [
  {
    start_date: '2020-03-10',
    end_date: '2020-03-30',
    similarity_score: 0.87,
    next_5day_return: 4.23,
  },
  {
    start_date: '2022-06-15',
    end_date: '2022-07-05',
    similarity_score: 0.73,
    next_5day_return: -1.82,
  },
  {
    start_date: '2024-01-08',
    end_date: '2024-01-28',
    similarity_score: 0.65,
    next_5day_return: 2.11,
  },
];

export default function AnalogPanel() {
  const { data, loading, error } = useAnalogs(60_000);
  const analogs = data && data.length > 0 ? data : (!loading ? MOCK_ANALOGS : []);

  return (
    <div id="analog-panel" className="flex flex-col gap-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-mist">
          Historical Analogs
        </h3>
        {error && !data && (
          <span className="text-[10px] text-ash px-2 py-0.5 rounded-full bg-slate-deep border border-steel/40">
            Demo data
          </span>
        )}
      </div>

      {/* Cards */}
      {loading ? (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <div className="space-y-3">
          {analogs.slice(0, 3).map((analog, i) => (
            <AnalogCard key={`${analog.start_date}-${analog.end_date}`} analog={analog} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
