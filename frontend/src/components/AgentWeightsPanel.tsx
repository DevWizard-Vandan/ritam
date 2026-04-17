import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useAgentsStats } from '../hooks';
import type { AgentStat } from '../types';

const BASELINE_WEIGHT = 1.0;
const MAX_WEIGHT_SCALE = 2.0;

function WeightBar({ weight }: { weight: number }) {
  const isAbove = weight >= BASELINE_WEIGHT;
  const pct = Math.min((weight / MAX_WEIGHT_SCALE) * 100, 100);

  return (
    <div className="flex items-center gap-3">
      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={`h-full rounded-full ${isAbove ? 'bg-blue-500' : 'bg-red-400'}`}
        />
      </div>
      <span className={`w-12 text-right font-mono text-xs ${isAbove ? 'text-slate-700' : 'text-red-500'}`}>
        {weight.toFixed(3)}
      </span>
    </div>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-t border-slate-200 animate-pulse">
      <td className="px-4 py-3"><div className="h-3 w-28 rounded bg-slate-200" /></td>
      <td className="px-4 py-3"><div className="h-2.5 rounded-full bg-slate-100" /></td>
      <td className="px-4 py-3"><div className="h-3 w-12 rounded bg-slate-200" /></td>
      <td className="hidden px-4 py-3 sm:table-cell"><div className="h-3 w-12 rounded bg-slate-200" /></td>
      <td className="hidden px-4 py-3 md:table-cell"><div className="h-3 w-10 rounded bg-slate-200" /></td>
      <td className="hidden px-4 py-3 lg:table-cell"><div className="h-3 w-24 rounded bg-slate-200" /></td>
    </tr>
  );
}

function AgentRow({ stat }: { stat: AgentStat }) {
  const acc7d = stat.accuracy_7d != null ? `${(stat.accuracy_7d * 100).toFixed(1)}%` : '--';
  const acc30d = stat.accuracy_30d != null ? `${(stat.accuracy_30d * 100).toFixed(1)}%` : '--';
  const lastUpdated = stat.last_updated
    ? new Date(stat.last_updated).toLocaleDateString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    : '--';

  return (
    <tr className="border-t border-slate-200 transition-colors hover:bg-slate-50">
      <td className="px-4 py-3 text-sm font-medium text-slate-900">
        {stat.agent_name.replace(/Agent$/, '')}
      </td>
      <td className="min-w-[160px] px-4 py-3">
        <WeightBar weight={stat.weight} />
      </td>
      <td className="px-4 py-3 font-mono text-xs text-slate-700">{acc7d}</td>
      <td className="hidden px-4 py-3 font-mono text-xs text-slate-700 sm:table-cell">{acc30d}</td>
      <td className="hidden px-4 py-3 font-mono text-xs text-slate-500 md:table-cell">
        {stat.total_predictions ?? 0}
      </td>
      <td className="hidden px-4 py-3 font-mono text-xs text-slate-500 lg:table-cell">{lastUpdated}</td>
    </tr>
  );
}

export default function AgentWeightsPanel() {
  const { data, loading, error } = useAgentsStats(60_000);
  const sorted: AgentStat[] = useMemo(() => {
    if (!data?.agents) return [];
    return [...data.agents].sort((a, b) => b.weight - a.weight);
  }, [data]);

  return (
    <motion.section
      id="agent-weights-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.25 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="panel-label">Agent Weights</p>
            <p className="panel-value mt-3">{String(sorted.length).padStart(2, '0')}</p>
            <p className="mt-2 text-sm text-slate-600">
              RL weighting with live 7-day and 30-day hit rates.
            </p>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
            {error ? 'Offline' : data ? 'Live' : 'Loading'}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">
                <th className="px-4 py-2">Agent</th>
                <th className="px-4 py-2">Weight</th>
                <th className="px-4 py-2">7d Acc</th>
                <th className="hidden px-4 py-2 sm:table-cell">30d Acc</th>
                <th className="hidden px-4 py-2 md:table-cell">Predictions</th>
                <th className="hidden px-4 py-2 lg:table-cell">Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <>
                  {Array.from({ length: 5 }).map((_, index) => (
                    <SkeletonRow key={`skeleton-${index}`} />
                  ))}
                </>
              ) : sorted.length > 0 ? (
                sorted.map((stat) => <AgentRow key={stat.agent_name} stat={stat} />)
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-sm text-slate-500">
                    No agent data available yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {data?.updated_at && (
          <p className="border-t border-slate-200 pt-4 font-mono text-xs text-slate-500">
            Updated {new Date(data.updated_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
          </p>
        )}
      </div>
    </motion.section>
  );
}
