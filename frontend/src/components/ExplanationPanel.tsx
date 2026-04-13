import { useExplanation } from '../hooks';

const MOCK_EXPLANATION = `[RITAM Reasoning Engine — Gemma 4 E2B]

Current Market Assessment:
─────────────────────────
The Nifty 50 index is consolidating near the 22,400 level
after a sharp intraday recovery. Today's session saw initial
weakness driven by overnight sell-off in US futures, but
domestic institutional buying absorbed supply near 22,200.

Key Observations:
• FII net sellers of ₹1,240 Cr in cash segment
• DII net buyers of ₹1,850 Cr — strong domestic support
• India VIX elevated at 16.2 — moderate caution warranted
• Sentiment score via FinBERT: +0.18 (mildly bullish)

Regime Classification: RECOVERY
Historical Analog Match: March 2020 bounce (73% similarity)
→ Analog outcome: +4.2% over next 5 sessions

Recommendation: HOLD with mild bullish bias.
The system maintains a hold stance given conflicting
FII/DII signals, but the historical analog and positive
sentiment tilt suggest upside probability is elevated.

Confidence: 68%  •  Timeframe: 20 minutes
──────────────────────────────────────────
Generated at ${new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST`;

export default function ExplanationPanel() {
  const { data, loading } = useExplanation(60_000);

  const explanation = data?.explanation || MOCK_EXPLANATION;

  return (
    <div
      id="explanation-panel"
      className="glass-card p-6 sm:p-7 flex flex-col gap-4 animate-slide-up"
      style={{ animationDelay: '0.3s' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-mist">
          Gemma Explanation
        </h3>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-slow" />
          <span className="text-[10px] text-ash uppercase tracking-wider">
            {data ? 'Live' : 'Demo'}
          </span>
        </div>
      </div>

      {/* Explanation text container with scrolling */}
      <div className="relative flex-1 min-h-0">
        {loading ? (
          <div className="space-y-2 animate-pulse">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="h-3 rounded bg-steel/30"
                style={{ width: `${60 + Math.random() * 40}%` }}
              />
            ))}
          </div>
        ) : (
          <div
            className="overflow-y-auto max-h-[340px] pr-2"
          >
            <pre className="font-mono text-xs sm:text-[13px] leading-relaxed text-silver whitespace-pre-wrap break-words selection:bg-accent-dim">
              {explanation}
            </pre>
          </div>
        )}
      </div>

      {/* Footer */}
      {data?.timestamp && (
        <div className="pt-3 border-t border-steel/30">
          <p className="text-[10px] text-ash">
            Generated: {new Date(data.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
          </p>
        </div>
      )}
    </div>
  );
}
