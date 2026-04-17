import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'framer-motion';

type LoginPageProps = {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onLogin: (email: string) => void;
};

export default function LoginPage({
  theme,
  onToggleTheme,
  onLogin,
}: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError('Please provide both email and password.');
      return;
    }

    setError('');
    onLogin(trimmedEmail);
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen px-4 py-10 sm:px-6"
    >
      <div className="mx-auto flex min-h-[80vh] max-w-5xl items-center justify-center">
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="panel-card w-full max-w-md p-7"
        >
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <p className="panel-label">Welcome Back</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">RITAM Login</h1>
              <p className="mt-2 text-sm text-slate-600">
                Sign in to access live predictions, analogs, and sandbox simulation.
              </p>
            </div>
            <button
              type="button"
              onClick={onToggleTheme}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
            >
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
          </div>

          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="email" className="panel-label">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@ritam.ai"
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="password" className="panel-label">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}

            <button
              type="submit"
              className="mt-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              Sign In
            </button>
          </form>
        </motion.section>
      </div>
    </motion.div>
  );
}
