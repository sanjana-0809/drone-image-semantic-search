import { cookies } from 'next/headers';
import { COOKIE_NAME } from '../../../../lib/auth-server';

export const dynamic = 'force-dynamic';

export async function POST() {
  const store = await cookies();
  store.delete(COOKIE_NAME);
  return Response.json({ ok: true });
}
