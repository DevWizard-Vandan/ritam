import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useSandbox } from '../hooks';
import SandboxChart from './SandboxChart';

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const MIN_DATE_ISO = '1990-01-01';
const PLACEHOLDERS = [
  'What if RBI cuts rates by 1%?',
  'What if crude jumps 12% overnight?',
  'What if the Fed surprises with a hike?',
  'What if election risk spikes into the open?',
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

function getRegimeMeta(regime: string): { label: string; className: string } {
  const normalized = regime.toLowerCase();
  if (normalized.includes('crisis') || normalized.includes('sell') || normalized.includes('down')) {
    return {
      label: 'Crisis',
      className: 'border border-red-200 bg-red-50 text-red-700',
    };
  }
  if (normalized.includes('range')) {
    return {
      label: 'Ranging',
      className: 'border border-amber-200 bg-amber-50 text-amber-700',
    };
  }
  return {
    label: 'Bullish',
    className: 'border border-green-200 bg-green-50 text-green-700',
  };
}

function sourceLabel(dataSource: 'db' | 'yfinance' | 'gemini_pure', date: string): string {
  const year = new Date(`${date}T00:00:00Z`).getUTCFullYear();
  if (dataSource === 'db') return `DB · ${year}`;
  if (dataSource === 'yfinance') return `yfinance · ${year}`;
  return 'Gemini only';
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

  const selectedIso = useMemo(() => dateFromOffset(MIN_DATE_ISO, dateOffset), [dateOffset]);
  const selectedLabel = formatMonthYear(selectedIso);
  const confidencePct = result ? Math.round(result.confidence <= 1 ? result.confidence * 100 : result.confidence) : 0;
  const regimeMeta = getRegimeMeta(result?.regime ?? 'ranging');

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
      // Error surfaced through hook state.
    }
  }

  function onReset() {
    setDateOffset(maxOffset);
    setInlineError(null);
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="panel-label">Scenario Sandbox</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{selectedLabel}</p>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Replay history, inject a condition, and let the reasoning stack simulate the next move.
            </p>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
            Gemini scenario engine
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="panel-label">Timeline</label>
            <button
              type="button"
              onClick={onReset}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
            >
              Reset
            </button>
          </div>
          <input
            type="range"
            min={0}
            max={maxOffset}
            value={dateOffset}
            onChange={(event) => setDateOffset(Number(event.target.value))}
            className="w-full cursor-pointer"
          />
          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Selected <span className="font-mono text-slate-900">{selectedLabel}</span>
            </span>
            <span className="font-mono text-slate-500">{selectedIso}</span>
          </div>
          <div className="relative pt-4">
            <div className="h-px bg-slate-200" />
            {MILESTONES.map((milestone) => {
              const positionPct = (getDayOffset(MIN_DATE_ISO, `${milestone.year}-01-01`) / maxOffset) * 100;
              return (
                <div
                  key={milestone.year}
                  className="absolute top-0 -translate-x-1/2"
                  style={{ left: `${Math.min(100, Math.max(0, positionPct))}%` }}
                >
                  <div className="h-2.5 w-2.5 rounded-full border border-slate-200 bg-white" />
                  <p className="mt-2 whitespace-nowrap text-[11px] text-slate-400">
                    {milestone.year} · {milestone.label}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-3">
          <label className="panel-label">Condition</label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={condition}
              onChange={(event) => setCondition(event.target.value)}
              placeholder={PLACEHOLDERS[placeholderIndex]}
              className="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={onRun}
              disabled={loading}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            >
              Run
            </button>
          </div>
          {inlineError && <p className="text-sm text-red-600">{inlineError}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        {loading && (
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-blue-500" />
            <span>Gemini is reasoning...</span>
          </div>
        )}

        <SandboxChart result={result} />

        {result && (
          <div className="flex flex-col gap-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="panel-muted p-4">
                <p className="panel-label">Regime</p>
                <span className={`mt-3 inline-flex rounded-full px-3 py-1.5 text-sm font-medium ${regimeMeta.className}`}>
                  {regimeMeta.label}
                </span>
              </div>
              <div className="panel-muted p-4">
                <p className="panel-label">Confidence</p>
                <p className="mt-3 font-mono text-2xl font-semibold text-slate-900">{confidencePct}%</p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${confidencePct}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    className="h-full rounded-full bg-blue-500"
                  />
                </div>
              </div>
              <div className="panel-muted p-4">
                <p className="panel-label">Source</p>
                <p className="mt-3 text-sm font-medium text-slate-900">
                  {sourceLabel(result.data_source, result.date)}
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-slate-100 bg-slate-50 p-4 text-sm leading-relaxed text-slate-600">
              {result.narrative}
            </div>
          </div>
        )}
      </div>
    </motion.section>
  );
}
