import { NextResponse } from 'next/server';

const COOKIE_NAME = 'app_session';

// Web Crypto (Edge runtime) equivalent of the Node sha256 used in auth-server.js.
async function sessionToken(secret) {
  const data = new TextEncoder().encode(`${secret}:drone-auth`);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function middleware(req) {
  const secret = process.env.ACCESS_PASSWORD || '';
  if (!secret) return NextResponse.next(); // auth disabled when unconfigured

  const { pathname } = req.nextUrl;

  // Always-public paths: the sign-in page and its auth routes.
  if (pathname.startsWith('/signin') || pathname.startsWith('/api/auth')) {
    return NextResponse.next();
  }

  const token = req.cookies.get(COOKIE_NAME)?.value;
  const valid = token && token === (await sessionToken(secret));
  if (valid) return NextResponse.next();

  // Proxy API calls return JSON 401 themselves; only redirect actual page views.
  if (pathname.startsWith('/api')) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = '/signin';
  url.search = '';
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
