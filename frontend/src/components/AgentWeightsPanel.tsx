import { useMemo } from 'react';
import { useAgentsStats } from '../hooks';
import type { AgentStat } from '../types';

const BASELINE_WEIGHT = 1.0;

/* ── Weight bar sub-component ── */
function WeightBar({ weight }: { weight: number }) {
  const isAbove = weight >= BASELINE_WEIGHT;
  const pct = Math.min((weight / 2) * 100, 100); // scale: 2.0 = 100%
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-2 rounded-full bg-slate-deep/80 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            isAbove ? 'bg-signal-buy' : 'bg-signal-sell'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`text-xs font-semibold tabular-nums w-10 text-right ${
          isAbove ? 'text-signal-buy' : 'text-signal-sell'
        }`}
      >
        {weight.toFixed(3)}
      </span>
    </div>
  );
}

/* ── Skeleton row ── */
function SkeletonRow() {
  return (
    <tr className="animate-pulse border-t border-steel/20">
      <td className="py-3 px-4"><div className="h-3 w-32 rounded bg-steel/30" /></td>
      <td className="py-3 px-4"><div className="h-2 w-full rounded-full bg-steel/30" /></td>
      <td className="py-3 px-4"><div className="h-3 w-12 rounded bg-steel/30" /></td>
      <td className="py-3 px-4 hidden sm:table-cell"><div className="h-3 w-12 rounded bg-steel/30" /></td>
      <td className="py-3 px-4 hidden md:table-cell"><div className="h-3 w-10 rounded bg-steel/30" /></td>
      <td className="py-3 px-4 hidden lg:table-cell"><div className="h-3 w-24 rounded bg-steel/30" /></td>
    </tr>
  );
}

/* ── Agent row ── */
function AgentRow({ stat }: { stat: AgentStat }) {
  const acc7d = stat.accuracy_7d != null ? `${(stat.accuracy_7d * 100).toFixed(1)}%` : '—';
  const acc30d = stat.accuracy_30d != null ? `${(stat.accuracy_30d * 100).toFixed(1)}%` : '—';
  const lastUpdated = stat.last_updated
    ? new Date(stat.last_updated).toLocaleDateString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    : '—';

  const shortName = stat.agent_name.replace(/Agent$/, '');

  return (
    <tr className="border-t border-steel/20 hover:bg-slate-deep/30 transition-colors">
      <td className="py-3 px-4">
        <span className="text-xs font-medium text-frost whitespace-nowrap">{shortName}</span>
      </td>
      <td className="py-3 px-4 min-w-[120px]">
        <WeightBar weight={stat.weight} />
      </td>
      <td className="py-3 px-4 text-xs tabular-nums text-mist">{acc7d}</td>
      <td className="py-3 px-4 hidden sm:table-cell text-xs tabular-nums text-mist">{acc30d}</td>
      <td className="py-3 px-4 hidden md:table-cell text-xs tabular-nums text-ash">
        {stat.total_predictions ?? 0}
      </td>
      <td className="py-3 px-4 hidden lg:table-cell text-[10px] text-ash whitespace-nowrap">
        {lastUpdated}
      </td>
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
    <div
      id="agent-weights-panel"
      className="glass-card p-6 sm:p-7 flex flex-col gap-4 animate-slide-up"
      style={{ animationDelay: '0.4s' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-mist">
          Agent Weights
        </h3>
        <div className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              error ? 'bg-signal-sell' : 'bg-signal-buy'
            } animate-pulse-slow`}
          />
          <span className="text-[10px] text-ash uppercase tracking-wider">
            {error ? 'Offline' : data ? 'Live' : 'Loading'}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto -mx-2">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-ash">
              <th className="py-2 px-4 font-medium">Agent</th>
              <th className="py-2 px-4 font-medium">Weight</th>
              <th className="py-2 px-4 font-medium">7d Acc</th>
              <th className="py-2 px-4 hidden sm:table-cell font-medium">30d Acc</th>
              <th className="py-2 px-4 hidden md:table-cell font-medium">Predictions</th>
              <th className="py-2 px-4 hidden lg:table-cell font-medium">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <>
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))}
              </>
            ) : sorted.length > 0 ? (
              sorted.map((stat) => (
                <AgentRow key={stat.agent_name} stat={stat} />
              ))
            ) : (
              <tr>
                <td colSpan={6} className="py-8 text-center text-sm text-ash">
                  No agent data available yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Footer timestamp */}
      {data?.updated_at && (
        <p className="text-[10px] text-ash border-t border-steel/20 pt-3">
          Updated:{' '}
          {new Date(data.updated_at).toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
          })}
        </p>
      )}
    </div>
  );
}
