'use client';

import { useState } from 'react';
import { Search, Eye, X, Layers, ScanLine, Palette } from 'lucide-react';
import { searchImages } from '../../lib/api';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);
    try {
      const data = await searchImages(query.trim());
      setResults(data);
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const exampleQueries = [
    'construction site with cranes',
    'vehicles on road',
    'water body near buildings',
    'solar panels on rooftop',
    'green vegetation area',
  ];

  return (
    <div>
      {/* ─── Search Bar ──────────────────────── */}
      <div className="max-w-3xl mx-auto mb-10">
        {!searched && (
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-3 bg-gradient-to-r from-white to-brand-400 bg-clip-text text-transparent">
              Search drone imagery with words
            </h2>
            <p className="text-[var(--text-muted)] text-sm">
              Type what you're looking for in plain English — the AI understands visual meaning.
            </p>
          </div>
        )}

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
            />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. construction site with scaffolding near water..."
              className="search-input pl-11"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="btn-primary flex items-center gap-2 whitespace-nowrap"
          >
            {loading ? <span className="spinner" /> : <Search size={16} />}
            Search
          </button>
        </form>

        {/* Example queries */}
        {!searched && (
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {exampleQueries.map((eq) => (
              <button
                key={eq}
                onClick={() => {
                  setQuery(eq);
                  setTimeout(() => handleSearch(), 50);
                }}
                className="tag hover:border-brand-400 hover:text-brand-400 transition cursor-pointer"
              >
                {eq}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ─── Results ─────────────────────────── */}
      {loading && (
        <div className="image-grid">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card-glow overflow-hidden">
              <div className="skeleton h-48 w-full" />
              <div className="p-4 space-y-2">
                <div className="skeleton h-4 w-3/4" />
                <div className="skeleton h-3 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-center py-20">
          <ScanLine size={48} className="mx-auto mb-4 text-[var(--text-muted)]" />
          <p className="text-[var(--text-secondary)] text-lg">No matching images found</p>
          <p className="text-[var(--text-muted)] text-sm mt-1">Try a different query or upload more images</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-5">
            <p className="text-sm text-[var(--text-muted)]">
              <span className="text-brand-400 font-semibold">{results.length}</span> results for &quot;{query}&quot;
            </p>
          </div>

          <div className="image-grid">
            {results.map((result) => (
              <div
                key={result.image_id}
                className="card-glow overflow-hidden cursor-pointer group"
                onClick={() => setSelectedImage(result)}
              >
                {/* Image */}
                <div className="relative h-52 overflow-hidden bg-surface-800">
                  <img
                    src={`$\{result.image_url\}`}
                    alt={result.caption || result.filename}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                  {/* Score badge */}
                  <div className="absolute top-3 right-3 score-badge">
                    {(result.similarity_score * 100).toFixed(1)}%
                  </div>
                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
                    <span className="text-white text-xs flex items-center gap-1">
                      <Eye size={14} /> View details
                    </span>
                  </div>
                </div>

                {/* Metadata */}
                <div className="p-4">
                  <p className="text-sm text-[var(--text-primary)] line-clamp-2 mb-2">
                    {result.caption || 'No caption generated'}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {(result.detected_objects || []).slice(0, 4).map((obj, i) => (
                      <span key={i} className="tag text-[10px]">{obj}</span>
                    ))}
                    {(result.detected_objects || []).length > 4 && (
                      <span className="tag text-[10px]">+{result.detected_objects.length - 4}</span>
                    )}
                  </div>
                  {/* Color swatches */}
                  {result.dominant_colors && result.dominant_colors.length > 0 && (
                    <div className="flex gap-1 mt-3">
                      {result.dominant_colors.map((color, i) => (
                        <div
                          key={i}
                          className="w-5 h-5 rounded-full border border-white/10"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ─── Detail Modal ────────────────────── */}
      {selectedImage && (
        <ImageDetailModal
          image={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  );
}


function ImageDetailModal({ image, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="bg-[var(--surface-raised)] rounded-2xl border border-[var(--border)] max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <div className="flex justify-end p-4 pb-0">
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-white transition p-1"
          >
            <X size={20} />
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-6 p-6 pt-2">
          {/* Image */}
          <div className="rounded-xl overflow-hidden bg-surface-800">
            <img
              src={`$\{image.image_url\}`}
              alt={image.caption || image.filename}
              className="w-full h-auto object-contain max-h-[500px]"
            />
          </div>

          {/* Metadata */}
          <div className="space-y-5">
            {/* Similarity score */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-[var(--text-muted)] uppercase tracking-wider">Similarity Score</span>
                <span className="score-badge text-sm">
                  {(image.similarity_score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-500 to-purple-500 rounded-full transition-all"
                  style={{ width: `${image.similarity_score * 100}%` }}
                />
              </div>
            </div>

            {/* Caption */}
            <div>
              <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Layers size={13} /> AI Caption
              </h4>
              <p className="text-[var(--text-primary)] text-sm leading-relaxed">
                {image.caption || 'No caption available'}
              </p>
            </div>

            {/* Detected Objects */}
            {image.detected_objects && image.detected_objects.length > 0 && (
              <div>
                <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <ScanLine size={13} /> Detected Objects
                </h4>
                <div className="flex flex-wrap gap-2">
                  {image.detected_objects.map((obj, i) => (
                    <span key={i} className="tag">{obj}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Dominant Colors */}
            {image.dominant_colors && image.dominant_colors.length > 0 && (
              <div>
                <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Palette size={13} /> Dominant Colors
                </h4>
                <div className="flex gap-2">
                  {image.dominant_colors.map((color, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div
                        className="w-8 h-8 rounded-lg border border-white/10"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-xs font-mono text-[var(--text-muted)]">{color}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* OCR Text */}
            {image.ocr_text && (
              <div>
                <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
                  Extracted Text (OCR)
                </h4>
                <p className="text-sm text-[var(--text-secondary)] font-mono bg-surface-800 p-3 rounded-lg">
                  {image.ocr_text}
                </p>
              </div>
            )}

            {/* Filename */}
            <div className="pt-3 border-t border-[var(--border)]">
              <p className="text-xs text-[var(--text-muted)]">
                <span className="font-mono">{image.filename}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


