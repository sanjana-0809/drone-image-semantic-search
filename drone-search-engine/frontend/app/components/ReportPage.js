'use client';

import { useState, useEffect } from 'react';
import { FileText, Download, RefreshCw, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { generateReport, getReport, exportReportPDF } from '../../lib/api';

function isHexColor(color) {
  return /^#[0-9a-fA-F]{6}$/.test(color);
}

export default function ReportPage() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getReport()
      .then((data) => {
        if (data) setReport(data.report_data || data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateReport();
      setReport(data.report);
    } catch (err) {
      setError(err.message || 'Failed to generate report. Make sure images have finished processing.');
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    try {
      await exportReportPDF();
    } catch (err) {
      setError(`PDF export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const formatContent = (content) => {
    if (!content) return null;

    return content.split('\n').map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-3" />;

      if (trimmed.startsWith('# ')) {
        return (
          <h2 key={i} className="text-xl font-bold text-white mt-8 mb-3 flex items-center gap-2">
            <Sparkles size={18} className="text-cyan-300" />
            {trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '')}
          </h2>
        );
      }

      if (trimmed.startsWith('## ') || trimmed.startsWith('### ')) {
        return (
          <h3 key={i} className="text-lg font-semibold text-white mt-6 mb-2">
            {trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '')}
          </h3>
        );
      }

      if (/^\d+\.\s+[A-Z]/.test(trimmed)) {
        return (
          <h3 key={i} className="text-lg font-semibold text-cyan-300 mt-8 mb-3 border-b border-[var(--border)] pb-2">
            {trimmed.replace(/\*\*/g, '')}
          </h3>
        );
      }

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return (
          <div key={i} className="flex gap-2 ml-4 mb-1.5">
            <span className="text-cyan-300 mt-1.5 flex-shrink-0">-</span>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              {trimmed.replace(/^[-*]\s*/, '').replace(/\*\*/g, '')}
            </p>
          </div>
        );
      }

      if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
        return (
          <h4 key={i} className="text-sm font-semibold text-white mt-4 mb-1">
            {trimmed.replace(/\*\*/g, '')}
          </h4>
        );
      }

      return (
        <p key={i} className="text-sm text-[var(--text-secondary)] leading-relaxed mb-2">
          {trimmed.replace(/\*\*/g, '')}
        </p>
      );
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="spinner" />
      </div>
    );
  }

  const palette = (report?.color_palette || []).filter(isHexColor);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-start justify-between mb-8 gap-4">
        <div>
          <h2 className="text-2xl font-bold mb-1">Site Intelligence Report</h2>
          <p className="text-[var(--text-muted)] text-sm">
            AI-generated analysis of your processed drone image collection.
          </p>
        </div>

        <div className="flex gap-2 flex-wrap justify-end">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating}
            className="btn-primary flex items-center gap-2"
          >
            {generating ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <RefreshCw size={16} />
            )}
            {generating ? 'Generating' : report ? 'Regenerate' : 'Generate'}
          </button>

          {report && (
            <button
              type="button"
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

      {error && (
        <div className="card-glow p-4 mb-6 border-red-500/30 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-300 font-medium">Error</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">{error}</p>
          </div>
        </div>
      )}

      {generating && (
        <div className="card-glow p-12 text-center">
          <Loader2 size={48} className="mx-auto mb-4 text-cyan-300 animate-spin" />
          <p className="text-lg font-semibold mb-2">Analyzing image collection...</p>
          <p className="text-sm text-[var(--text-muted)]">
            Clustering images, summarizing themes, and drafting the report.
          </p>
        </div>
      )}

      {!report && !generating && (
        <div className="card-glow p-12 text-center">
          <FileText size={48} className="mx-auto mb-4 text-[var(--text-muted)]" />
          <p className="text-lg font-semibold mb-2">No report generated yet</p>
          <p className="text-sm text-[var(--text-muted)] mb-6">
            Upload images and wait for processing to complete before generating a report.
          </p>
          <button type="button" onClick={handleGenerate} className="btn-primary">
            <Sparkles size={16} className="inline mr-2" />
            Generate Report
          </button>
        </div>
      )}

      {report && !generating && (
        <div className="card-glow p-8">
          <div className="border-b border-[var(--border)] pb-6 mb-6">
            <p className="text-xs text-cyan-300 font-mono tracking-wider mb-2">SKYLARK DRONES</p>
            <h2 className="text-2xl font-bold mb-2">
              {report.title || 'Site Intelligence Report'}
            </h2>
            <p className="text-sm text-[var(--text-muted)]">
              {report.subtitle || `Generated ${new Date().toLocaleDateString()}`}
            </p>

            <div className="flex gap-6 mt-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-cyan-300">
                  {report.image_count || 0}
                </span>
                <span className="text-xs text-[var(--text-muted)]">Images<br />Analyzed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-emerald-300">
                  {report.cluster_count || 0}
                </span>
                <span className="text-xs text-[var(--text-muted)]">Visual<br />Clusters</span>
              </div>
              {palette.length > 0 && (
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    {palette.slice(0, 5).map((color) => (
                      <span
                        key={color}
                        className="w-6 h-6 rounded-md border border-white/10"
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">Color<br />Palette</span>
                </div>
              )}
            </div>
          </div>

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
                    const maxCount = Math.max(...Object.values(report.object_frequencies), 1);
                    return (
                      <div key={obj} className="flex items-center gap-3">
                        <span className="text-xs text-[var(--text-secondary)] w-24 text-right font-mono truncate">
                          {obj}
                        </span>
                        <div className="flex-1 h-5 bg-surface-800 rounded overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-cyan-500/60 to-emerald-400/40 rounded"
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

          <div className="report-content">
            {formatContent(report.content)}
          </div>

          <div className="border-t border-[var(--border)] mt-8 pt-4">
            <p className="text-xs text-[var(--text-muted)] text-center">
              Generated by Drone Image Semantic Search Engine - {report.generated_at ? new Date(report.generated_at).toLocaleString() : 'N/A'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
