import crypto from 'crypto';
import { cookies } from 'next/headers';

export const COOKIE_NAME = 'app_session';

// The shared gate password. When unset, auth is disabled so the app still runs
// without configuration (matches the backend, which is open when APP_ACCESS_KEY
// is unset).
const PASSWORD = process.env.ACCESS_PASSWORD || '';

export function authEnabled() {
  return Boolean(PASSWORD);
}

// Opaque session value stored in the httpOnly cookie. Derived from the password
// so it cannot be forged without knowing it, and never reveals the password.
export function sessionToken() {
  return crypto.createHash('sha256').update(`${PASSWORD}:drone-auth`).digest('hex');
}

export function passwordMatches(candidate) {
  if (!PASSWORD) return true;
  if (typeof candidate !== 'string' || candidate.length !== PASSWORD.length) return false;
  return crypto.timingSafeEqual(Buffer.from(candidate), Buffer.from(PASSWORD));
}

export async function isAuthed() {
  if (!PASSWORD) return true;
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value === sessionToken();
}
