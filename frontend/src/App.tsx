import { useState, useEffect } from 'react';
import SignalPanel from './components/SignalPanel';
import AccuracyPanel from './components/AccuracyPanel';
import AnalogPanel from './components/AnalogPanel';
import ExplanationPanel from './components/ExplanationPanel';

function useCurrentTime() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

function isMarketHours(now: Date): boolean {
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const hour = ist.getHours();
  const minute = ist.getMinutes();
  const totalMin = hour * 60 + minute;
  const day = ist.getDay();
  // NSE: Mon-Fri, 9:15 AM - 3:30 PM IST
  return day >= 1 && day <= 5 && totalMin >= 555 && totalMin <= 930;
}

export default function App() {
  const now = useCurrentTime();
  const marketOpen = isMarketHours(now);

  const timeStr = now.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  return (
    <div className="min-h-screen bg-void text-frost flex flex-col">
      {/* ── Top Nav Bar ── */}
      <header className="sticky top-0 z-50 border-b border-steel/30 bg-abyss/80 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          {/* Left: Brand */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-cyan flex items-center justify-center">
              <span className="text-sm font-black text-white">R</span>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wide text-frost leading-none">
                RITAM
              </h1>
              <p className="text-[10px] text-ash tracking-[0.15em] uppercase leading-none mt-0.5">
                Perception Engine
              </p>
            </div>
          </div>

          {/* Center: Market status */}
          <div className="hidden sm:flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-deep/60 border border-steel/30">
              <span
                className={`w-2 h-2 rounded-full ${
                  marketOpen ? 'bg-signal-buy animate-pulse-slow' : 'bg-signal-sell'
                }`}
              />
              <span className="text-xs font-medium text-mist">
                NSE {marketOpen ? 'Open' : 'Closed'}
              </span>
            </div>
            <span className="text-xs text-ash font-mono tabular-nums">{timeStr} IST</span>
          </div>

          {/* Right: Badge */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-ash uppercase tracking-wider hidden md:inline">
              Nifty 50 Intelligence
            </span>
            <div className="w-px h-4 bg-steel/40 hidden md:block" />
            <span className="text-[10px] font-mono text-ash">v2.0</span>
          </div>
        </div>
      </header>

      {/* ── Main Dashboard Grid ── */}
      <main className="flex-1 max-w-[1600px] mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 auto-rows-min">
          {/* Signal Panel — top center, spans 7 cols on large screens */}
          <div className="lg:col-span-7 lg:row-span-1">
            <SignalPanel />
          </div>

          {/* Accuracy Panel — top right, spans 5 cols */}
          <div className="lg:col-span-5 lg:row-span-1">
            <AccuracyPanel />
          </div>

          {/* Analog Panel — bottom left, spans 5 cols */}
          <div className="lg:col-span-5 lg:row-span-1">
            <AnalogPanel />
          </div>

          {/* Explanation Panel — bottom right, spans 7 cols */}
          <div className="lg:col-span-7 lg:row-span-1">
            <ExplanationPanel />
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-steel/20 bg-abyss/60">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <p className="text-[10px] text-ash">
            RITAM — Not prediction. Perception.
          </p>
          <p className="text-[10px] text-ash">
            Data refreshes every 60s during market hours
          </p>
        </div>
      </footer>
    </div>
  );
}
