import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import SignalPanel from './components/SignalPanel';
import AccuracyPanel from './components/AccuracyPanel';
import AnalogPanel from './components/AnalogPanel';
import ExplanationPanel from './components/ExplanationPanel';
import AgentWeightsPanel from './components/AgentWeightsPanel';
import PredictionChart from './components/PredictionChart';
import SandboxPanel from './components/SandboxPanel';
import SettingsPanel from './components/SettingsPanel';
import LoginPage from './components/LoginPage';

const THEME_STORAGE_KEY = 'ritam_theme';
const AUTH_STORAGE_KEY = 'ritam_auth';

type DashboardTab = 'live' | 'sandbox' | 'settings';
type ThemeMode = 'light' | 'dark';

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
  return day >= 1 && day <= 5 && totalMin >= 555 && totalMin <= 930;
}

export default function App() {
  const now = useCurrentTime();
  const marketOpen = isMarketHours(now);
  const [activeTab, setActiveTab] = useState<DashboardTab>('live');
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    return storedTheme === 'dark' ? 'dark' : 'light';
  });
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem(AUTH_STORAGE_KEY) === 'true';
  });

  const tabs: Array<{ id: DashboardTab; label: string }> = [
    { id: 'live', label: 'Live' },
    { id: 'sandbox', label: 'Sandbox' },
    { id: 'settings', label: 'Settings' },
  ];

  const timeStr = now.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  }

  function handleLogin(email: string) {
    localStorage.setItem(AUTH_STORAGE_KEY, 'true');
    localStorage.setItem('ritam_user_email', email);
    setIsAuthenticated(true);
  }

  function handleLogout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setIsAuthenticated(false);
    setActiveTab('live');
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        theme={theme}
        onToggleTheme={toggleTheme}
        onLogin={handleLogin}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-transparent text-slate-900"
    >
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <header className="mb-8 border-b border-slate-200 pb-4">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-xl font-semibold text-slate-900 shadow-card">
                R
              </div>
              <div className="space-y-1">
                <p className="text-lg font-semibold tracking-tight text-slate-900">RITAM</p>
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
                  Not prediction. Perception.
                </p>
              </div>
            </div>

            <div className="flex flex-1 flex-col gap-4 lg:max-w-4xl lg:flex-row lg:items-center lg:justify-end">
              <p className="text-sm italic text-slate-400 lg:text-right">
                Markets don&apos;t repeat. They rhyme.
              </p>
              <div className="self-start rounded-full border border-slate-200 bg-white px-4 py-2 shadow-card lg:self-auto">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-sm font-medium text-slate-900">Live</span>
                </div>
                <p className="mt-1 font-mono text-xs text-slate-500">
                  {marketOpen ? 'NSE Open' : 'NSE Closed'} · {timeStr} IST
                </p>
              </div>
            </div>
          </div>
        </header>

        <nav className="mb-8 border-b border-slate-200">
          <div className="flex gap-8">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative pb-3 text-sm font-medium transition-colors ${
                    isActive ? 'text-blue-600' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {tab.label}
                  {isActive && (
                    <motion.span
                      layoutId="dashboard-active-tab"
                      className="absolute inset-x-0 bottom-[-1px] h-0.5 rounded-full bg-blue-600"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </nav>

        <main className="flex-1">
          <AnimatePresence mode="wait">
            {activeTab === 'live' ? (
              <motion.div
                key="live"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="grid auto-rows-min grid-cols-1 gap-5 sm:gap-6 lg:grid-cols-12"
              >
                <div className="lg:col-span-12">
                  <PredictionChart />
                </div>
                <div className="lg:col-span-7">
                  <SignalPanel />
                </div>
                <div className="lg:col-span-5">
                  <AccuracyPanel />
                </div>
                <div className="lg:col-span-5">
                  <AnalogPanel />
                </div>
                <div className="lg:col-span-7">
                  <ExplanationPanel />
                </div>
                <div className="lg:col-span-12">
                  <AgentWeightsPanel />
                </div>
              </motion.div>
            ) : activeTab === 'sandbox' ? (
              <motion.div
                key="sandbox"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <SandboxPanel />
              </motion.div>
            ) : (
              <motion.div
                key="settings"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <SettingsPanel
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  onLogout={handleLogout}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <footer className="mt-8 border-t border-slate-200 pt-4">
          <div className="flex flex-col gap-2 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <p>RITAM · Not prediction. Perception.</p>
            <p className="font-mono">Refresh cadence: 60s · Asia/Kolkata</p>
          </div>
        </footer>
      </div>
    </motion.div>
  );
}
