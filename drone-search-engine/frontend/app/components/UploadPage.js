'use client';

import { useState, useRef, useCallback } from 'react';
import { Upload, Image, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadImages } from '../../lib/api';

export default function UploadPage({ onComplete }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [results, setResults] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback((fileList) => {
    const imageFiles = Array.from(fileList).filter((f) =>
      f.type.startsWith('image/')
    );
    setFiles((prev) => [...prev, ...imageFiles]);
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setResults([]);
    setProgress({ done: 0, total: files.length });

    const uploadResults = [];

    // Upload one by one for progress tracking
    for (let i = 0; i < files.length; i++) {
      try {
        const result = await uploadImages([files[i]]);
        uploadResults.push({
          filename: files[i].name,
          status: 'success',
          caption: result.ai_results?.caption || '',
        });
      } catch (err) {
        uploadResults.push({
          filename: files[i].name,
          status: 'error',
          error: err.message,
        });
      }
      setProgress({ done: i + 1, total: files.length });
    }

    setResults(uploadResults);
    setUploading(false);
    setFiles([]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const successCount = results.filter((r) => r.status === 'success').length;
  const errorCount = results.filter((r) => r.status === 'error').length;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold mb-2">Upload Drone Images</h2>
        <p className="text-[var(--text-muted)] text-sm">
          Upload aerial images to be processed by the AI pipeline and indexed for semantic search.
        </p>
      </div>

      {/* ─── Drop Zone ────────────────────────── */}
      {!uploading && results.length === 0 && (
        <div
          className={`drop-zone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <Upload size={40} className="mx-auto mb-4 text-[var(--text-muted)]" />
          <p className="text-[var(--text-primary)] font-medium mb-1">
            Drag & drop images here
          </p>
          <p className="text-[var(--text-muted)] text-sm">
            or click to browse — supports JPG, PNG, WebP, TIFF
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*"
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
        </div>
      )}

      {/* ─── Selected Files ───────────────────── */}
      {files.length > 0 && !uploading && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-[var(--text-secondary)]">
              {files.length} image{files.length > 1 ? 's' : ''} selected
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setFiles([])}
                className="btn-secondary text-sm py-2 px-4"
              >
                Clear all
              </button>
              <button onClick={handleUpload} className="btn-primary text-sm py-2 px-4">
                Upload & Process
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {files.map((file, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)]"
              >
                <Image size={16} className="text-brand-400 flex-shrink-0" />
                <span className="text-sm text-[var(--text-primary)] truncate flex-1">
                  {file.name}
                </span>
                <span className="text-xs text-[var(--text-muted)] font-mono">
                  {(file.size / 1024).toFixed(0)} KB
                </span>
                <button
                  onClick={() => removeFile(i)}
                  className="text-[var(--text-muted)] hover:text-red-400 transition text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Upload Progress ──────────────────── */}
      {uploading && (
        <div className="card-glow p-8 text-center">
          <Loader2 size={40} className="mx-auto mb-4 text-brand-400 animate-spin" />
          <p className="text-lg font-semibold mb-2">Processing images...</p>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            Running EasyOCR + BLIP-2 + YOLOv8 + CLIP on each image
          </p>

          {/* Progress bar */}
          <div className="w-full max-w-md mx-auto">
            <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1">
              <span>{progress.done} of {progress.total}</span>
              <span>{((progress.done / progress.total) * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-500 to-purple-500 rounded-full transition-all duration-300"
                style={{ width: `${(progress.done / progress.total) * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* ─── Results ──────────────────────────── */}
      {results.length > 0 && !uploading && (
        <div className="mt-6">
          {/* Summary */}
          <div className="card-glow p-6 mb-4 text-center">
            <CheckCircle size={36} className="mx-auto mb-3 text-emerald-400" />
            <p className="text-lg font-semibold mb-1">Upload Complete</p>
            <p className="text-sm text-[var(--text-muted)]">
              {successCount} processed successfully
              {errorCount > 0 && `, ${errorCount} failed`}
            </p>
            <div className="flex gap-3 justify-center mt-4">
              <button
                onClick={() => {
                  setResults([]);
                  setFiles([]);
                }}
                className="btn-secondary text-sm py-2 px-4"
              >
                Upload more
              </button>
              <button
                onClick={onComplete}
                className="btn-primary text-sm py-2 px-4"
              >
                Go to Search
              </button>
            </div>
          </div>

          {/* Individual results */}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {results.map((r, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)]"
              >
                {r.status === 'success' ? (
                  <CheckCircle size={16} className="text-emerald-400 flex-shrink-0" />
                ) : (
                  <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
                )}
                <span className="text-sm text-[var(--text-primary)] truncate flex-1">
                  {r.filename}
                </span>
                {r.caption && (
                  <span className="text-xs text-[var(--text-muted)] truncate max-w-[200px]">
                    {r.caption}
                  </span>
                )}
                {r.error && (
                  <span className="text-xs text-red-400 truncate max-w-[200px]">
                    {r.error}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
