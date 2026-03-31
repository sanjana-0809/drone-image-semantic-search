/**
 * API client for the Drone Search Engine backend.
 * All calls go through Next.js rewrites → FastAPI at localhost:8000
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function fixImageUrl(url) {
  if (!url) return url;
  if (url.startsWith('http://localhost:8000')) {
    return url.replace('http://localhost:8000', API_BASE);
  }
  if (url.startsWith('/images/')) {
    return `${API_BASE}${url}`;
  }
  return url;
}

export async function uploadImages(files) {
  const formData = new FormData();
  
  if (files.length === 1) {
    formData.append('file', files[0]);
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
    return res.json();
  }
  
  // Batch upload
  for (const file of files) {
    formData.append('files', file);
  }
  const res = await fetch(`${API_BASE}/upload-batch`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Batch upload failed: ${res.statusText}`);
  return res.json();
}

export async function searchImages(query, topK = 10) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function getImagesList() {
  const res = await fetch(`${API_BASE}/images-list`);
  if (!res.ok) throw new Error(`Failed to fetch images: ${res.statusText}`);
  return res.json();
}

export async function getImageDetail(imageId) {
  const res = await fetch(`${API_BASE}/image/${imageId}`);
  if (!res.ok) throw new Error(`Failed to fetch image: ${res.statusText}`);
  return res.json();
}

export async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`Failed to fetch stats: ${res.statusText}`);
  return res.json();
}

export async function generateReport() {
  const res = await fetch(`${API_BASE}/generate-report`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Report generation failed: ${res.statusText}`);
  return res.json();
}

export async function getReport() {
  const res = await fetch(`${API_BASE}/report`);
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch report: ${res.statusText}`);
  }
  return res.json();
}

export async function exportReportPDF() {
  const res = await fetch(`${API_BASE}/export-report`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`PDF export failed: ${res.statusText}`);
  
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'site_intelligence_report.pdf';
  a.click();
  URL.revokeObjectURL(url);
}
