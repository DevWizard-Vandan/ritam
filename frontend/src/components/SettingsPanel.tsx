import { motion } from 'framer-motion';

type SettingsPanelProps = {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onLogout: () => void;
};

export default function SettingsPanel({
  theme,
  onToggleTheme,
  onLogout,
}: SettingsPanelProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="panel-card p-6"
    >
      <div className="flex flex-col gap-6">
        <div>
          <p className="panel-label">Settings</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
            Workspace Preferences
          </p>
          <p className="mt-2 text-sm text-slate-600">
            Control local dashboard behavior and account session settings.
          </p>
        </div>

        <div className="panel-muted flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">Dark Mode</p>
            <p className="mt-1 text-sm text-slate-600">
              Switch between light and dark dashboard themes.
            </p>
          </div>
          <button
            type="button"
            onClick={onToggleTheme}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              theme === 'dark'
                ? 'bg-slate-800 text-slate-100 hover:bg-slate-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {theme === 'dark' ? 'Disable Dark Mode' : 'Enable Dark Mode'}
          </button>
        </div>

        <div className="panel-muted flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">Session</p>
            <p className="mt-1 text-sm text-slate-600">
              End this local session and return to the login page.
            </p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100"
          >
            Logout
          </button>
        </div>
      </div>
    </motion.section>
  );
}
