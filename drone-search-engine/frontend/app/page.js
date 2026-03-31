'use client';

import { useState, useEffect } from 'react';
import { Search, Upload, FileText, BarChart3, Satellite, Zap } from 'lucide-react';
import SearchPage from './components/SearchPage';
import UploadPage from './components/UploadPage';
import ReportPage from './components/ReportPage';
import { getStats } from '../lib/api';

const tabs = [
  { id: 'search', label: 'Search', icon: Search },
  { id: 'upload', label: 'Upload', icon: Upload },
  { id: 'report', label: 'Report', icon: FileText },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState('search');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, [activeTab]);

  return (
    <div className="relative z-10 min-h-screen">
      {/* ─── Header ─────────────────────────────── */}
      <header className="border-b border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center">
              <Satellite size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Drone Search Engine</h1>
              <p className="text-[11px] text-[var(--text-muted)] font-mono tracking-wider"></p>
            </div>
          </div>

          {/* Stats pills */}
          {stats && (
            <div className="hidden md:flex items-center gap-4 text-xs font-mono text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                {stats.total_images} images indexed
              </span>
              <span>{stats.processed_images} processed</span>
            </div>
          )}

          {/* Nav tabs */}
          <nav className="flex gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`nav-link flex items-center gap-2 ${
                    activeTab === tab.id ? 'active' : ''
                  }`}
                >
                  <Icon size={16} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* ─── Main Content ──────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'search' && <SearchPage />}
        {activeTab === 'upload' && <UploadPage onComplete={() => setActiveTab('search')} />}
        {activeTab === 'report' && <ReportPage />}
      </main>

      {/* ─── Footer ─────────────────────────────── */}
      <footer className="border-t border-[var(--border)] mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-xs text-[var(--text-muted)]">
          <span>Drone Image Semantic Search Engine</span>
          <span className="flex items-center gap-1">
            <Zap size={12} className="text-brand-400" />
            Powered by CLIP + BLIP-2 + YOLOv8 + Claude
          </span>
        </div>
      </footer>
    </div>
  );
}
