import { cookies } from 'next/headers';
import { COOKIE_NAME, authEnabled, passwordMatches, sessionToken } from '../../../../lib/auth-server';

export const dynamic = 'force-dynamic';

export async function POST(req) {
  if (!authEnabled()) {
    return Response.json({ ok: true, note: 'Auth is disabled (ACCESS_PASSWORD not set).' });
  }

  const body = await req.json().catch(() => ({}));
  if (!passwordMatches(body?.password)) {
    return Response.json({ error: 'Incorrect password' }, { status: 401 });
  }

  const store = await cookies();
  store.set(COOKIE_NAME, sessionToken(), {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 7, // 7 days
  });
  return Response.json({ ok: true });
}
