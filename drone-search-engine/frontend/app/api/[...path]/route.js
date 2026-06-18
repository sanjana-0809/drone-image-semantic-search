import { isAuthed } from '../../../lib/auth-server';

export const dynamic = 'force-dynamic';

const BACKEND = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
// The backend access key. Reuses the gate password so there is a single shared
// secret to configure. Attached here, server-side, so it never reaches the browser.
const ACCESS_KEY = process.env.ACCESS_PASSWORD || '';

async function handler(req, ctx) {
  if (!(await isAuthed())) {
    return Response.json({ detail: 'Not authenticated' }, { status: 401 });
  }

  const { path } = await ctx.params;
  const search = new URL(req.url).search;
  const target = `${BACKEND}/${(path || []).join('/')}${search}`;

  const headers = new Headers();
  const contentType = req.headers.get('content-type');
  if (contentType) headers.set('content-type', contentType);
  if (ACCESS_KEY) headers.set('authorization', `Bearer ${ACCESS_KEY}`);

  const init = { method: req.method, headers, redirect: 'manual' };
  if (!['GET', 'HEAD'].includes(req.method)) {
    init.body = await req.arrayBuffer();
  }

  let backendRes;
  try {
    backendRes = await fetch(target, init);
  } catch {
    return Response.json(
      { detail: 'Cannot reach the backend. Check BACKEND_URL.' },
      { status: 502 },
    );
  }

  const respHeaders = new Headers();
  for (const key of ['content-type', 'content-disposition', 'cache-control']) {
    const value = backendRes.headers.get(key);
    if (value) respHeaders.set(key, value);
  }
  return new Response(backendRes.body, { status: backendRes.status, headers: respHeaders });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
