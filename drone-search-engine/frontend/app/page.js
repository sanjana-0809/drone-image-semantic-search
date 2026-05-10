'use client';

import { useState, useEffect } from 'react';
import { Search, Upload, FileText, Satellite, Zap, AlertTriangle } from 'lucide-react';
import SearchPage from './components/SearchPage';
import UploadPage from './components/UploadPage';
import ReportPage from './components/ReportPage';
import { checkBackendHealth, getStats } from '../lib/api';

const tabs = [
  { id: 'search', label: 'Search', icon: Search },
  { id: 'upload', label: 'Upload', icon: Upload },
  { id: 'report', label: 'Report', icon: FileText },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState('search');
  const [stats, setStats] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);
  const [backendError, setBackendError] = useState('');

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats(null));

    let cancelled = false;
    checkBackendHealth()
      .then((health) => {
        if (cancelled) return;
        setBackendHealth(health);
        setBackendError('');
      })
      .catch((err) => {
        if (cancelled) return;
        setBackendHealth(null);
        setBackendError(err.message || 'Backend unavailable');
      });

    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  const backendStatus = backendError ? 'offline' : backendHealth?.status || 'checking';
  const backendStatusClass = {
    healthy: 'bg-emerald-500',
    degraded: 'bg-amber-400',
    unhealthy: 'bg-red-500',
    offline: 'bg-red-500',
    checking: 'bg-slate-500',
  }[backendStatus] || 'bg-slate-500';
  const backendTitle = backendError || backendHealth?.services?.vector_store?.error || 'Backend connected';

  return (
    <div className="relative z-10 min-h-screen flex flex-col">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-brand-500 flex items-center justify-center flex-shrink-0">
              <Satellite size={18} className="text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold tracking-tight truncate">Drone Search Engine</h1>
              <p className="sr-only">Semantic search for aerial imagery</p>
            </div>
          </div>

          <div className="hidden lg:flex items-center gap-4 text-xs font-mono text-[var(--text-muted)]">
            <span className="flex items-center gap-1.5" title={backendTitle}>
              <span className={`w-2 h-2 rounded-full ${backendStatusClass}`} />
              backend {backendStatus}
            </span>
            {stats && (
              <>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                {stats.total_images} images
              </span>
              <span>{stats.processed_images} processed</span>
              {stats.failed_images > 0 && (
                <span className="flex items-center gap-1 text-amber-300">
                  <AlertTriangle size={12} />
                  {stats.failed_images} failed
                </span>
              )}
              </>
            )}
          </div>

          <nav className="flex gap-1" aria-label="Primary">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`nav-link flex items-center gap-2 ${
                    activeTab === tab.id ? 'active' : ''
                  }`}
                  aria-current={activeTab === tab.id ? 'page' : undefined}
                >
                  <Icon size={16} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 w-full flex-1">
        {activeTab === 'search' && <SearchPage />}
        {activeTab === 'upload' && <UploadPage onComplete={() => setActiveTab('search')} />}
        {activeTab === 'report' && <ReportPage />}
      </main>

      <footer className="border-t border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between gap-4 text-xs text-[var(--text-muted)]">
          <span>Drone Image Semantic Search Engine</span>
          <span className="hidden sm:flex items-center gap-1">
            <Zap size={12} className="text-cyan-300" />
            CLIP + BLIP + YOLOv8 + Groq
          </span>
        </div>
      </footer>
    </div>
  );
}
