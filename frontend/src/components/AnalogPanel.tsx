import { motion } from 'framer-motion';
import { useAnalogs } from '../hooks';
import type { Analog } from '../types';

function SimilarityArc({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const circumference = 2 * Math.PI * 26;
  const offset = circumference - score * circumference;

  return (
    <div className="relative h-16 w-16 flex-shrink-0">
      <svg viewBox="0 0 60 60" className="h-full w-full -rotate-90">
        <circle cx="30" cy="30" r="26" fill="none" stroke="#E2E8F0" strokeWidth="4" />
        <circle
          cx="30"
          cy="30"
          r="26"
          fill="none"
          stroke="url(#analog-gradient)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
        <defs>
          <linearGradient id="analog-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#60A5FA" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
        </defs>
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-sm font-semibold text-slate-900">
        {pct}%
      </span>
    </div>
  );
}

function AnalogRow({ analog }: { analog: Analog }) {
  const isPositive = analog.next_5day_return >= 0;

  return (
    <div className="panel-muted flex items-center gap-4 p-4 transition-colors hover:bg-white">
      <SimilarityArc score={analog.similarity_score} />
      <div className="min-w-0 flex-1">
        <p className="panel-label">Matched Window</p>
        <p className="mt-2 truncate text-sm font-semibold text-slate-900">
          {analog.start_date} to {analog.end_date}
        </p>
        <div className="mt-3 flex items-center gap-3">
          <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
            Analog Outcome
          </span>
          <span className={`font-mono text-sm font-semibold ${isPositive ? 'text-green-700' : 'text-red-700'}`}>
            {isPositive ? '+' : ''}
            {analog.next_5day_return.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="panel-muted flex items-center gap-4 p-4 animate-pulse">
      <div className="h-16 w-16 rounded-full bg-slate-200" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-24 rounded bg-slate-200" />
        <div className="h-4 w-48 rounded bg-slate-200" />
        <div className="h-3 w-28 rounded bg-slate-200" />
      </div>
    </div>
  );
}

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
  const analogs = data && data.length > 0 ? data : !loading ? MOCK_ANALOGS : [];
  const topSimilarity = analogs.length > 0 ? `${Math.round(analogs[0].similarity_score * 100)}%` : '--';

  return (
    <motion.section
      id="analog-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="panel-label">Historical Analogs</p>
            <p className="panel-value mt-3">{topSimilarity}</p>
            <p className="mt-2 text-sm text-slate-600">
              Closest market rhymes ranked by pattern similarity.
            </p>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
            {error && !data ? 'Demo data' : 'Live analogs'}
          </div>
        </div>

        <div className="space-y-3">
          {loading ? (
            <>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </>
          ) : (
            analogs.slice(0, 3).map((analog) => (
              <AnalogRow key={`${analog.start_date}-${analog.end_date}`} analog={analog} />
            ))
          )}
        </div>
      </div>
    </motion.section>
  );
}
