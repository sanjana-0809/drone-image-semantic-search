'use client';

import { useState, useEffect } from 'react';
import { FileText, Download, RefreshCw, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { generateReport, getReport, exportReportPDF } from '../../lib/api';

export default function ReportPage() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  // Try loading existing report on mount
  useEffect(() => {
    setLoading(true);
    getReport()
      .then((data) => {
        if (data) {
          // Handle nested report_data from DB
          const reportContent = data.report_data || data;
          setReport(reportContent);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateReport();
      setReport(data.report);
    } catch (err) {
      setError(err.message || 'Failed to generate report. Make sure you have processed images.');
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportReportPDF();
    } catch (err) {
      setError('PDF export failed: ' + err.message);
    } finally {
      setExporting(false);
    }
  };

  // Format report content — handle markdown-like sections
  const formatContent = (content) => {
    if (!content) return null;

    const lines = content.split('\n');
    const elements = [];

    lines.forEach((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) {
        elements.push(<div key={i} className="h-3" />);
        return;
      }

      // Main headers
      if (trimmed.startsWith('# ')) {
        elements.push(
          <h2 key={i} className="text-xl font-bold text-white mt-8 mb-3 flex items-center gap-2">
            <Sparkles size={18} className="text-brand-400" />
            {trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '')}
          </h2>
        );
      }
      // Sub headers
      else if (trimmed.startsWith('## ') || trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={i} className="text-lg font-semibold text-white mt-6 mb-2">
            {trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '')}
          </h3>
        );
      }
      // Numbered sections (1. EXECUTIVE SUMMARY etc.)
      else if (/^\d+\.\s+[A-Z]/.test(trimmed)) {
        elements.push(
          <h3 key={i} className="text-lg font-semibold text-brand-400 mt-8 mb-3 border-b border-[var(--border)] pb-2">
            {trimmed.replace(/\*\*/g, '')}
          </h3>
        );
      }
      // Bullet points
      else if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
        elements.push(
          <div key={i} className="flex gap-2 ml-4 mb-1.5">
            <span className="text-brand-400 mt-1.5 flex-shrink-0">•</span>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              {trimmed.replace(/^[-•]\s*/, '').replace(/\*\*/g, '')}
            </p>
          </div>
        );
      }
      // Bold section titles within text
      else if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
        elements.push(
          <h4 key={i} className="text-sm font-semibold text-white mt-4 mb-1">
            {trimmed.replace(/\*\*/g, '')}
          </h4>
        );
      }
      // Regular paragraphs
      else {
        elements.push(
          <p key={i} className="text-sm text-[var(--text-secondary)] leading-relaxed mb-2">
            {trimmed.replace(/\*\*/g, '')}
          </p>
        );
      }
    });

    return elements;
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold mb-1">Site Intelligence Report</h2>
          <p className="text-[var(--text-muted)] text-sm">
            AI-generated analysis of your drone image collection — powered by Claude
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-primary flex items-center gap-2"
          >
            {generating ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <RefreshCw size={16} />
            )}
            {generating ? 'Generating...' : report ? 'Regenerate' : 'Generate Report'}
          </button>

          {report && (
            <button
              onClick={handleExport}
              disabled={exporting}
              className="btn-secondary flex items-center gap-2"
            >
              {exporting ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Download size={16} />
              )}
              Export PDF
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card-glow p-4 mb-6 border-red-500/30 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-400 font-medium">Error</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Generating state */}
      {generating && (
        <div className="card-glow p-12 text-center">
          <Loader2 size={48} className="mx-auto mb-4 text-brand-400 animate-spin" />
          <p className="text-lg font-semibold mb-2">Analyzing image collection...</p>
          <p className="text-sm text-[var(--text-muted)]">
            Clustering images → Summarizing themes → Claude is writing the report
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-2">This takes 15–30 seconds</p>
        </div>
      )}

      {/* No report yet */}
      {!report && !generating && (
        <div className="card-glow p-12 text-center">
          <FileText size={48} className="mx-auto mb-4 text-[var(--text-muted)]" />
          <p className="text-lg font-semibold mb-2">No report generated yet</p>
          <p className="text-sm text-[var(--text-muted)] mb-6">
            Upload and process drone images first, then generate a Site Intelligence Report.
          </p>
          <button onClick={handleGenerate} className="btn-primary">
            <Sparkles size={16} className="inline mr-2" />
            Generate Report
          </button>
        </div>
      )}

      {/* Report content */}
      {report && !generating && (
        <div className="card-glow p-8">
          {/* Report header */}
          <div className="border-b border-[var(--border)] pb-6 mb-6">
            <p className="text-xs text-brand-400 font-mono tracking-wider mb-2">SKYLARK DRONES</p>
            <h2 className="text-2xl font-bold mb-2">
              {report.title || 'Site Intelligence Report'}
            </h2>
            <p className="text-sm text-[var(--text-muted)]">
              {report.subtitle || `Generated ${new Date().toLocaleDateString()}`}
            </p>

            {/* Stats */}
            <div className="flex gap-6 mt-4">
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-brand-400">
                  {report.image_count || 0}
                </span>
                <span className="text-xs text-[var(--text-muted)]">Images<br/>Analyzed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-purple-400">
                  {report.cluster_count || 0}
                </span>
                <span className="text-xs text-[var(--text-muted)]">Visual<br/>Clusters</span>
              </div>
              {report.color_palette && report.color_palette.length > 0 && (
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    {report.color_palette.slice(0, 5).map((c, i) => (
                      <div
                        key={i}
                        className="w-6 h-6 rounded-md border border-white/10"
                        style={{ backgroundColor: c }}
                        title={c}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">Color<br/>Palette</span>
                </div>
              )}
            </div>
          </div>

          {/* Object frequency bar */}
          {report.object_frequencies && Object.keys(report.object_frequencies).length > 0 && (
            <div className="mb-8">
              <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-3">
                Detected Object Frequency
              </h4>
              <div className="space-y-1.5">
                {Object.entries(report.object_frequencies)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 8)
                  .map(([obj, count]) => {
                    const maxCount = Math.max(...Object.values(report.object_frequencies));
                    return (
                      <div key={obj} className="flex items-center gap-3">
                        <span className="text-xs text-[var(--text-secondary)] w-24 text-right font-mono">
                          {obj}
                        </span>
                        <div className="flex-1 h-5 bg-surface-800 rounded overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-brand-500/60 to-brand-400/40 rounded"
                            style={{ width: `${(count / maxCount) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-[var(--text-muted)] font-mono w-8">
                          {count}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Report body */}
          <div className="report-content">
            {formatContent(report.content)}
          </div>

          {/* Footer */}
          <div className="border-t border-[var(--border)] mt-8 pt-4">
            <p className="text-xs text-[var(--text-muted)] text-center">
              Generated by Drone Image Semantic Search Engine · {report.generated_at ? new Date(report.generated_at).toLocaleString() : 'N/A'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
