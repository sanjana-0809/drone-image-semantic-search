'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, Satellite, Loader2, AlertCircle } from 'lucide-react';

export default function SignIn() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Incorrect password');
      }
      router.replace('/');
      router.refresh();
    } catch (err) {
      setError(err.message || 'Sign in failed');
      setLoading(false);
    }
  };

  return (
    <div className="relative z-10 min-h-screen flex items-center justify-center px-6">
      <div className="card-glow p-8 w-full max-w-sm">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-brand-500 flex items-center justify-center mb-3">
            <Satellite size={22} className="text-white" />
          </div>
          <h1 className="text-xl font-bold">Drone Search Engine</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Enter the access password to continue.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Access password"
              className="search-input pl-11"
              autoFocus
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-red-300">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Lock size={16} />}
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
