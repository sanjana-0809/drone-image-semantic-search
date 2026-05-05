'use client';

import { useEffect, useState } from 'react';
import { Search, Eye, X, Layers, ScanLine, Palette, AlertCircle } from 'lucide-react';
import { searchImages } from '../../lib/api';

const exampleQueries = [
  'construction site with cranes',
  'vehicles on road',
  'water body near buildings',
  'solar panels on rooftop',
  'green vegetation area',
];

function isHexColor(color) {
  return /^#[0-9a-fA-F]{6}$/.test(color);
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [error, setError] = useState('');

  const handleSearch = async (e, overrideQuery) => {
    e?.preventDefault();
    const searchQuery = (overrideQuery ?? query).trim();
    if (!searchQuery) return;

    setQuery(searchQuery);
    setLoading(true);
    setSearched(true);
    setError('');
    try {
      const data = await searchImages(searchQuery);
      setResults(data);
    } catch (err) {
      setError(err.message || 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="max-w-3xl mx-auto mb-10">
        {!searched && (
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-3 bg-gradient-to-r from-white via-cyan-100 to-brand-400 bg-clip-text text-transparent">
              Search drone imagery with words
            </h2>
            <p className="text-[var(--text-muted)] text-sm">
              Type what you are looking for in plain English.
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
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. construction site with scaffolding near water"
              className="search-input pl-11"
              maxLength={500}
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

        {!searched && (
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {exampleQueries.map((example) => (
              <button
                key={example}
                type="button"
                onClick={(event) => handleSearch(event, example)}
                className="tag hover:border-cyan-400 hover:text-cyan-300 transition cursor-pointer"
              >
                {example}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="max-w-3xl mx-auto card-glow p-4 mb-6 border-red-500/30 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm text-red-300 font-medium">Search unavailable</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">{error}</p>
          </div>
        </div>
      )}

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

      {!loading && searched && results.length === 0 && !error && (
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
              <span className="text-cyan-300 font-semibold">{results.length}</span> results for &quot;{query}&quot;
            </p>
          </div>

          <div className="image-grid">
            {results.map((result) => (
              <button
                key={result.image_id}
                type="button"
                className="card-glow overflow-hidden cursor-pointer group text-left"
                onClick={() => setSelectedImage(result)}
              >
                <div className="relative h-52 overflow-hidden bg-surface-800">
                  {result.image_url ? (
                    <img
                      src={result.image_url}
                      alt={result.caption || result.filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-sm text-[var(--text-muted)]">
                      Image unavailable
                    </div>
                  )}
                  <div className="absolute top-3 right-3 score-badge">
                    {(result.similarity_score * 100).toFixed(1)}%
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
                    <span className="text-white text-xs flex items-center gap-1">
                      <Eye size={14} /> View details
                    </span>
                  </div>
                </div>

                <div className="p-4">
                  <p className="text-sm text-[var(--text-primary)] line-clamp-2 mb-2">
                    {result.caption || result.filename || 'Processing'}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {(result.detected_objects || []).slice(0, 4).map((obj) => (
                      <span key={obj} className="tag text-[10px]">{obj}</span>
                    ))}
                    {(result.detected_objects || []).length > 4 && (
                      <span className="tag text-[10px]">+{result.detected_objects.length - 4}</span>
                    )}
                  </div>
                  {result.dominant_colors?.length > 0 && (
                    <div className="flex gap-1 mt-3">
                      {result.dominant_colors.filter(isHexColor).map((color) => (
                        <span
                          key={color}
                          className="w-5 h-5 rounded-full border border-white/10"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </>
      )}

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
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="bg-[var(--surface-raised)] rounded-lg border border-[var(--border)] max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={image.caption || image.filename || 'Image details'}
      >
        <div className="flex justify-end p-4 pb-0">
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-white transition p-1"
            aria-label="Close image details"
            title="Close"
          >
            <X size={20} />
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-6 p-6 pt-2">
          <div className="rounded-lg overflow-hidden bg-surface-800">
            {image.image_url ? (
              <img
                src={image.image_url}
                alt={image.caption || image.filename}
                className="w-full h-auto object-contain max-h-[500px]"
              />
            ) : (
              <div className="min-h-[240px] flex items-center justify-center text-sm text-[var(--text-muted)]">
                Image unavailable
              </div>
            )}
          </div>

          <div className="space-y-5">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-[var(--text-muted)] uppercase tracking-wider">Similarity Score</span>
                <span className="score-badge text-sm">
                  {(image.similarity_score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-500 to-cyan-400 rounded-full transition-all"
                  style={{ width: `${Math.min(image.similarity_score * 100, 100)}%` }}
                />
              </div>
            </div>

            <div>
              <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Layers size={13} /> AI Caption
              </h4>
              <p className="text-[var(--text-primary)] text-sm leading-relaxed">
                {image.caption || 'No caption available'}
              </p>
            </div>

            {image.detected_objects?.length > 0 && (
              <div>
                <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <ScanLine size={13} /> Detected Objects
                </h4>
                <div className="flex flex-wrap gap-2">
                  {image.detected_objects.map((obj) => (
                    <span key={obj} className="tag">{obj}</span>
                  ))}
                </div>
              </div>
            )}

            {image.dominant_colors?.some(isHexColor) && (
              <div>
                <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Palette size={13} /> Dominant Colors
                </h4>
                <div className="flex flex-wrap gap-3">
                  {image.dominant_colors.filter(isHexColor).map((color) => (
                    <div key={color} className="flex items-center gap-2">
                      <span
                        className="w-8 h-8 rounded-lg border border-white/10"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-xs font-mono text-[var(--text-muted)]">{color}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {image.ocr_text && (
              <div>
                <h4 className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
                  Extracted Text
                </h4>
                <p className="text-sm text-[var(--text-secondary)] font-mono bg-surface-800 p-3 rounded-lg break-words">
                  {image.ocr_text}
                </p>
              </div>
            )}

            <div className="pt-3 border-t border-[var(--border)]">
              <p className="text-xs text-[var(--text-muted)] break-all">
                <span className="font-mono">{image.filename}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
