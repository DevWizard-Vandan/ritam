import { motion } from 'framer-motion';
import { useExplanation } from '../hooks';

const SKELETON_WIDTHS = ['96%', '88%', '92%', '74%', '81%', '69%', '85%', '72%'] as const;

const MOCK_EXPLANATION = `[RITAM Reasoning Engine - Gemini 2.5 Flash]

Current Market Assessment:
The Nifty 50 index is consolidating near the 22,400 level after a sharp intraday recovery. Today's session saw initial weakness driven by overnight selling in US futures, but domestic institutional buying absorbed supply near 22,200.

Key Observations:
- FII net sellers of Rs1,240 Cr in cash
- DII net buyers of Rs1,850 Cr supporting the tape
- India VIX elevated at 16.2, so caution remains justified
- FinBERT sentiment score: +0.18, mildly constructive

Regime Classification: Recovery
Historical Analog Match: March 2020 bounce (73% similarity)
Analog Outcome: +4.2% over the next 5 sessions

Recommendation:
Hold with a mild bullish bias. Conflicting flow signals keep conviction tempered, but the analog and sentiment stack still lean constructive.

Confidence: 68%
Timeframe: 20 minutes

Generated at ${new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST`;

export default function ExplanationPanel() {
  const { data, loading } = useExplanation(60_000);
  const explanation = data?.explanation || MOCK_EXPLANATION;

  return (
    <motion.section
      id="explanation-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className="panel-card p-6"
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="panel-label">Reasoning Narrative</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Gemini 2.5</p>
            <p className="mt-2 text-sm text-slate-600">
              Structured context from the active reasoning engine.
            </p>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
            {data ? 'Live' : 'Demo'}
          </div>
        </div>

        <div className="panel-muted min-h-0 flex-1 p-4">
          {loading ? (
            <div className="space-y-2 animate-pulse">
              {SKELETON_WIDTHS.map((width) => (
                <div key={width} className="h-3 rounded bg-slate-200" style={{ width }} />
              ))}
            </div>
          ) : (
            <div className="max-h-[340px] overflow-y-auto pr-2">
              <pre className="whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-slate-700">
                {explanation}
              </pre>
            </div>
          )}
        </div>

        {data?.timestamp && (
          <p className="border-t border-slate-200 pt-4 font-mono text-xs text-slate-500">
            Generated {new Date(data.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
          </p>
        )}
      </div>
    </motion.section>
  );
}
