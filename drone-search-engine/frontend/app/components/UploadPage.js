'use client';

import { useState, useRef, useCallback } from 'react';
import { Upload, Image, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react';
import { MAX_UPLOAD_SIZE_MB, uploadImages, validateImageFile } from '../../lib/api';

export default function UploadPage({ onComplete }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [results, setResults] = useState([]);
  const [rejections, setRejections] = useState([]);
  const [processingMsg, setProcessingMsg] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback((fileList) => {
    const accepted = [];
    const rejected = [];

    Array.from(fileList).forEach((file) => {
      const error = validateImageFile(file);
      if (error) {
        rejected.push({ filename: file.name, error });
      } else {
        accepted.push(file);
      }
    });

    setFiles((prev) => [...prev, ...accepted]);
    setRejections(rejected);
    setResults([]);
    setProcessingMsg('');
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
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
    setRejections([]);
    setProgress({ done: 0, total: files.length });

    const uploadResults = [];

    for (let i = 0; i < files.length; i += 1) {
      try {
        const result = await uploadImages([files[i]]);
        uploadResults.push({
          filename: files[i].name,
          status: 'queued',
          imageId: result.image_id,
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
    setProcessingMsg('Images uploaded and queued. AI processing continues in the background.');
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const successCount = results.filter((r) => r.status === 'queued').length;
  const errorCount = results.filter((r) => r.status === 'error').length;
  const uploadPercent = progress.total ? (progress.done / progress.total) * 100 : 0;

  return (
    <div className="max-w-3xl mx-auto">
      {processingMsg && (
        <div className="mb-4 p-3 rounded-lg bg-green-500/20 text-green-300 text-sm text-center">
          {processingMsg}
        </div>
      )}

      {rejections.length > 0 && (
        <div className="mb-4 p-4 rounded-lg border border-red-500/30 bg-red-500/10">
          <div className="flex items-center gap-2 text-sm text-red-300 font-medium mb-2">
            <AlertCircle size={16} />
            Some files were rejected
          </div>
          <div className="space-y-1">
            {rejections.map((item) => (
              <p key={`${item.filename}-${item.error}`} className="text-xs text-[var(--text-muted)]">
                <span className="font-mono">{item.filename}</span>: {item.error}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold mb-2">Upload Drone Images</h2>
        <p className="text-[var(--text-muted)] text-sm">
          JPG, PNG, WebP, TIFF, or BMP. Max {MAX_UPLOAD_SIZE_MB} MB per image.
        </p>
      </div>

      {!uploading && results.length === 0 && (
        <button
          type="button"
          className={`drop-zone w-full ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <Upload size={40} className="mx-auto mb-4 text-[var(--text-muted)]" />
          <span className="block text-[var(--text-primary)] font-medium mb-1">
            Drop images here
          </span>
          <span className="block text-[var(--text-muted)] text-sm">
            or click to browse
          </span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.webp,.tif,.tiff,.bmp,image/jpeg,image/png,image/webp,image/tiff,image/bmp"
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
        </button>
      )}

      {files.length > 0 && !uploading && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3 gap-3">
            <p className="text-sm text-[var(--text-secondary)]">
              {files.length} image{files.length > 1 ? 's' : ''} selected
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setFiles([])}
                className="btn-secondary text-sm py-2 px-4"
              >
                Clear all
              </button>
              <button type="button" onClick={handleUpload} className="btn-primary text-sm py-2 px-4">
                Upload
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {files.map((file, i) => (
              <div
                key={`${file.name}-${file.size}-${i}`}
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
                  type="button"
                  onClick={() => removeFile(i)}
                  className="text-[var(--text-muted)] hover:text-red-400 transition p-1"
                  aria-label={`Remove ${file.name}`}
                  title="Remove"
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {uploading && (
        <div className="card-glow p-8 text-center">
          <Loader2 size={40} className="mx-auto mb-4 text-brand-400 animate-spin" />
          <p className="text-lg font-semibold mb-2">Uploading images...</p>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            Each image is validated, stored, and queued for AI processing.
          </p>

          <div className="w-full max-w-md mx-auto">
            <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1">
              <span>{progress.done} of {progress.total}</span>
              <span>{uploadPercent.toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-500 to-cyan-400 rounded-full transition-all duration-300"
                style={{ width: `${uploadPercent}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {results.length > 0 && !uploading && (
        <div className="mt-6">
          <div className="card-glow p-6 mb-4 text-center">
            <CheckCircle size={36} className="mx-auto mb-3 text-emerald-400" />
            <p className="text-lg font-semibold mb-1">Upload Complete</p>
            <p className="text-sm text-[var(--text-muted)]">
              {successCount} queued
              {errorCount > 0 && `, ${errorCount} failed`}
            </p>
            <div className="flex gap-3 justify-center mt-4">
              <button
                type="button"
                onClick={() => {
                  setResults([]);
                  setFiles([]);
                }}
                className="btn-secondary text-sm py-2 px-4"
              >
                Upload more
              </button>
              <button
                type="button"
                onClick={onComplete}
                className="btn-primary text-sm py-2 px-4"
              >
                Go to Search
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {results.map((result, i) => (
              <div
                key={`${result.filename}-${i}`}
                className="flex items-center gap-3 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)]"
              >
                {result.status === 'queued' ? (
                  <CheckCircle size={16} className="text-emerald-400 flex-shrink-0" />
                ) : (
                  <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
                )}
                <span className="text-sm text-[var(--text-primary)] truncate flex-1">
                  {result.filename}
                </span>
                {result.error ? (
                  <span className="text-xs text-red-400 truncate max-w-[220px]">
                    {result.error}
                  </span>
                ) : (
                  <span className="text-xs text-[var(--text-muted)] font-mono">
                    queued
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
