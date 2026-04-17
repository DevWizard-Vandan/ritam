import { useEffect, useMemo, useState } from 'react';
import { useSandbox } from '../hooks';
import SandboxChart from './SandboxChart';

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const MIN_DATE_ISO = '1990-01-01';
const PLACEHOLDERS = [
  'What if RBI cuts rates by 1%...',
  'China invades Taiwan...',
  'If markets existed in the Mahabharata era...',
  'India wins Cricket World Cup tomorrow...',
] as const;

const MILESTONES = [
  { year: 1992, label: 'Harshad Mehta' },
  { year: 2000, label: 'Dotcom' },
  { year: 2008, label: 'GFC' },
  { year: 2020, label: 'COVID' },
  { year: 2024, label: 'Elections' },
] as const;

function isoDateOnly(date: Date): string {
  return date.toISOString().split('T')[0];
}

function parseIsoDate(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

function getDayOffset(baseIso: string, targetIso: string): number {
  const base = parseIsoDate(baseIso).getTime();
  const target = parseIsoDate(targetIso).getTime();
  return Math.round((target - base) / MS_PER_DAY);
}

function dateFromOffset(baseIso: string, offset: number): string {
  const base = parseIsoDate(baseIso).getTime();
  const date = new Date(base + offset * MS_PER_DAY);
  return isoDateOnly(date);
}

function formatMonthYear(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-IN', {
    timeZone: 'Asia/Kolkata',
    month: 'short',
    year: 'numeric',
  });
}

function getRegimeLabel(regime: string): string {
  const normalized = regime.toLowerCase();
  if (normalized.includes('crisis') || normalized.includes('sell') || normalized.includes('down')) {
    return '🔴 Crisis';
  }
  if (normalized.includes('range')) {
    return '🟡 Ranging';
  }
  return '🟢 Buy';
}

function confidenceBarColor(confidencePct: number): string {
  if (confidencePct > 70) return 'bg-emerald-500';
  if (confidencePct >= 40) return 'bg-yellow-400';
  return 'bg-red-500';
}

function sourceLabel(dataSource: 'db' | 'yfinance' | 'gemini_pure', date: string): string {
  if (dataSource === 'db') return `db (${new Date(`${date}T00:00:00Z`).getUTCFullYear()})`;
  if (dataSource === 'yfinance') return `yfinance (${new Date(`${date}T00:00:00Z`).getUTCFullYear()})`;
  return 'gemini_pure';
}

export default function SandboxPanel() {
  const todayIso = useMemo(() => isoDateOnly(new Date()), []);
  const maxOffset = useMemo(() => getDayOffset(MIN_DATE_ISO, todayIso), [todayIso]);
  const [dateOffset, setDateOffset] = useState(maxOffset);
  const [condition, setCondition] = useState('');
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const { run, result, loading, error } = useSandbox();

  useEffect(() => {
    const id = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDERS.length);
    }, 3_000);
    return () => clearInterval(id);
  }, []);

  const selectedIso = useMemo(
    () => dateFromOffset(MIN_DATE_ISO, dateOffset),
    [dateOffset],
  );

  const selectedLabel = formatMonthYear(selectedIso);
  const confidencePct = result ? Math.round(result.confidence <= 1 ? result.confidence * 100 : result.confidence) : 0;

  async function onRun() {
    const trimmedCondition = condition.trim();
    const includeDate = selectedIso !== todayIso;
    const includeCondition = trimmedCondition.length > 0;

    if (!includeDate && !includeCondition) {
      setInlineError('Please provide a date or a condition to run a sandbox scenario.');
      return;
    }

    setInlineError(null);

    const requestBody: { date?: string; condition?: string; candles_ahead?: number } = {};
    if (includeDate) requestBody.date = selectedIso;
    if (includeCondition) requestBody.condition = trimmedCondition;

    try {
      await run(requestBody);
    } catch {
      // Error surfaced through hook state
    }
  }

  function onReset() {
    setDateOffset(maxOffset);
    setInlineError(null);
  }

  return (
    <section className="glass-card p-6 sm:p-7 flex flex-col gap-5 animate-slide-up">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg sm:text-xl font-semibold text-frost">🧪 RITAM Sandbox — What If?</h2>
      </div>

      <div className="space-y-2">
        <label className="text-xs uppercase tracking-[0.18em] text-mist font-semibold">Timeline</label>
        <input
          type="range"
          min={0}
          max={maxOffset}
          value={dateOffset}
          onChange={(event) => setDateOffset(Number(event.target.value))}
          className="w-full accent-blue-500 cursor-pointer"
        />
        <div className="flex items-center justify-between text-sm text-ash">
          <span>Selected: <span className="text-frost font-medium">{selectedLabel}</span></span>
          <button
            type="button"
            className="px-3 py-1 rounded-md bg-slate-800 text-slate-200 hover:opacity-80 transition-opacity"
            onClick={onReset}
          >
            Reset
          </button>
        </div>
        <div className="relative pt-3 pb-1">
          <div className="h-px bg-slate-700/70" />
          {MILESTONES.map((milestone) => {
            const positionPct = (getDayOffset(MIN_DATE_ISO, `${milestone.year}-01-01`) / maxOffset) * 100;
            return (
              <div
                key={milestone.year}
                className="absolute top-0 -translate-x-1/2"
                style={{ left: `${Math.min(100, Math.max(0, positionPct))}%` }}
              >
                <div className="w-px h-3 bg-blue-400/80" />
                <p className="text-[10px] text-ash mt-1 whitespace-nowrap">
                  {milestone.year} ({milestone.label})
                </p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-xs uppercase tracking-[0.18em] text-mist font-semibold">Condition</label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={condition}
            onChange={(event) => setCondition(event.target.value)}
            placeholder={PLACEHOLDERS[placeholderIndex]}
            className="flex-1 rounded-md border border-slate-700 bg-[#0A0F1E] px-3 py-2 text-sm text-frost placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/70"
          />
          <button
            type="button"
            onClick={onRun}
            disabled={loading}
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
          >
            ▶ Run
          </button>
        </div>
        {inlineError && <p className="text-xs text-red-400">{inlineError}</p>}
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      {loading && (
        <p className="text-sm text-cyan animate-pulse">🧠 Gemini is reasoning...</p>
      )}

      <SandboxChart result={result} />

      {result && (
        <div className="space-y-3">
          <p className="text-sm text-frost">Regime: <span className="font-semibold">{getRegimeLabel(result.regime)}</span></p>
          <div>
            <div className="flex items-center justify-between text-sm text-frost mb-1">
              <span>Confidence</span>
              <span className="font-semibold">{confidencePct}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
              <div
                className={`h-full ${confidenceBarColor(confidencePct)} transition-all duration-700 ease-out`}
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>
          <p className="text-sm text-ash">Source: {sourceLabel(result.data_source, result.date)}</p>
          <div>
            <p className="text-sm text-frost mb-1">📖 Narrative:</p>
            <p className="text-sm text-slate-200 leading-relaxed">{result.narrative}</p>
          </div>
        </div>
      )}
    </section>
  );
}
