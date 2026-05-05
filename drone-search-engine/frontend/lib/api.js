/**
 * Browser API client for the Drone Search Engine backend.
 * Defaults to Next.js rewrites at /api, so local and deployed frontends can stay same-origin.
 */

const directApiBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
const API_BASE = directApiBase || '/api';
const DEFAULT_TIMEOUT_MS = 30000;
const REPORT_TIMEOUT_MS = 120000;

export const MAX_UPLOAD_SIZE_MB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB || 25);
export const ALLOWED_IMAGE_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/tiff',
  'image/x-tiff',
  'image/bmp',
  'image/x-ms-bmp',
]);
export const ALLOWED_IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'tif', 'tiff', 'bmp']);

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

function normalizeApiError(message) {
  if (Array.isArray(message)) {
    return message.map((item) => item.msg || item.message || JSON.stringify(item)).join(', ');
  }
  if (typeof message === 'string') return message;
  if (message && typeof message === 'object') return message.detail || message.message || JSON.stringify(message);
  return 'Request failed';
}

async function request(path, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(apiUrl(path), {
      ...options,
      signal: controller.signal,
    });

    if (!res.ok) {
      let message = res.statusText;
      try {
        const body = await res.json();
        message = normalizeApiError(body.detail || body);
      } catch {
        const text = await res.text();
        if (text) message = text;
      }
      throw new Error(message || `Request failed with status ${res.status}`);
    }

    return res;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. The backend may still be processing heavy AI work.');
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export function validateImageFile(file) {
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (!extension || !ALLOWED_IMAGE_EXTENSIONS.has(extension)) {
    return 'Unsupported image type. Use JPG, PNG, WebP, TIFF, or BMP.';
  }
  if (file.type && !ALLOWED_IMAGE_TYPES.has(file.type)) {
    return `Unsupported content type: ${file.type}`;
  }
  if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    return `Image is larger than ${MAX_UPLOAD_SIZE_MB} MB.`;
  }
  if (file.size === 0) {
    return 'Image file is empty.';
  }
  return null;
}

export function fixImageUrl(url) {
  if (!url || typeof url !== 'string') return '';
  if (url.startsWith('http://localhost:8000')) {
    return url.replace('http://localhost:8000', API_BASE);
  }
  if (url.startsWith('/images/')) {
    return `${API_BASE}${url}`;
  }
  if (url.startsWith('/api/images/') || url.startsWith('https://') || url.startsWith('http://')) {
    return url;
  }
  return '';
}

function normalizeImage(image) {
  return {
    ...image,
    image_url: fixImageUrl(image.image_url),
    detected_objects: Array.isArray(image.detected_objects) ? image.detected_objects : [],
    dominant_colors: Array.isArray(image.dominant_colors) ? image.dominant_colors : [],
  };
}

export async function uploadImages(files) {
  const formData = new FormData();

  if (files.length === 1) {
    formData.append('file', files[0]);
    const res = await request('/upload', {
      method: 'POST',
      body: formData,
    }, REPORT_TIMEOUT_MS);
    return res.json();
  }

  for (const file of files) {
    formData.append('files', file);
  }
  const res = await request('/upload-batch', {
    method: 'POST',
    body: formData,
  }, REPORT_TIMEOUT_MS);
  return res.json();
}

export async function searchImages(query, topK = 10) {
  const res = await request('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  const data = await res.json();
  return data.map(normalizeImage);
}

export async function getImagesList() {
  const res = await request('/images-list');
  const data = await res.json();
  return data.map(normalizeImage);
}

export async function getImageDetail(imageId) {
  const res = await request(`/image/${encodeURIComponent(imageId)}`);
  return normalizeImage(await res.json());
}

export async function getStats() {
  const res = await request('/stats');
  return res.json();
}

export async function generateReport() {
  const res = await request('/generate-report', {
    method: 'POST',
  }, REPORT_TIMEOUT_MS);
  return res.json();
}

export async function getReport() {
  try {
    const res = await request('/report');
    return res.json();
  } catch (err) {
    if (err.message.includes('No report generated')) return null;
    throw err;
  }
}

export async function exportReportPDF() {
  const res = await request('/export-report', {
    method: 'POST',
  }, REPORT_TIMEOUT_MS);

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'site_intelligence_report.pdf';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
