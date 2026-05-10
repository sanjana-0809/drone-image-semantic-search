/** @type {import('next').NextConfig} */

function parseHttpUrl(raw, envName) {
  const parsed = new URL(raw);
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`${envName} must use http or https`);
  }
  return parsed;
}

function backendUrl() {
  const raw = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  return parseHttpUrl(raw, 'BACKEND_URL').href.replace(/\/$/, '');
}

function optionalOrigin(raw) {
  if (!raw) return null;
  try {
    return parseHttpUrl(raw, 'NEXT_PUBLIC_API_URL').origin;
  } catch {
    return null;
  }
}

const backendTarget = backendUrl();
const backendOrigin = new URL(backendTarget).origin;
const isHostedBuild = process.env.VERCEL === '1' || Boolean(process.env.CI);
const isLocalBackend = ['http://localhost:8000', 'http://127.0.0.1:8000'].includes(backendOrigin);

if (isHostedBuild && isLocalBackend && process.env.ALLOW_LOCAL_BACKEND_URL !== 'true') {
  throw new Error(
    'Hosted deployment is missing a real backend URL. Set BACKEND_URL or NEXT_PUBLIC_API_URL to your Hugging Face FastAPI backend, not localhost:8000.'
  );
}

const apiOrigins = Array.from(new Set([
  'http://localhost:8000',
  'http://127.0.0.1:8000',
  backendOrigin,
  optionalOrigin(process.env.NEXT_PUBLIC_API_URL),
].filter(Boolean)));

const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'X-Frame-Options', value: 'DENY' },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
  },
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "base-uri 'self'",
      "object-src 'none'",
      "frame-ancestors 'none'",
      "form-action 'self'",
      `img-src 'self' blob: data: ${apiOrigins.join(' ')} https:`,
      `connect-src 'self' ${apiOrigins.join(' ')} https:`,
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      "font-src 'self' data:",
    ].join('; '),
  },
];

const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendTarget}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
