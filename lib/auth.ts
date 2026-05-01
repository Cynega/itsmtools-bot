// HMAC-firmado token de auth, compatible con Edge runtime (Web Crypto).
// Formato del cookie: "<expiry_unix_seconds>.<hmac_sha256_hex>"

export const AUTH_COOKIE = "auth";
export const AUTH_MAX_AGE = 60 * 60 * 24 * 30; // 30 días

function getSecret(): string {
  const s = process.env.AUTH_SECRET;
  if (!s || s.length < 32) {
    throw new Error("AUTH_SECRET missing or too short (need ≥32 chars)");
  }
  return s;
}

function bytesToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function hmacHex(secret: string, msg: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return bytesToHex(sig);
}

export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) {
    out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return out === 0;
}

export async function sign(maxAgeSeconds: number): Promise<string> {
  const expiry = Math.floor(Date.now() / 1000) + maxAgeSeconds;
  const expiryStr = String(expiry);
  const mac = await hmacHex(getSecret(), expiryStr);
  return `${expiryStr}.${mac}`;
}

export async function verify(token: string | undefined): Promise<boolean> {
  if (!token) return false;
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [expiryStr, mac] = parts;
  const expiry = Number(expiryStr);
  if (!Number.isFinite(expiry)) return false;
  if (expiry < Math.floor(Date.now() / 1000)) return false;

  let secret: string;
  try {
    secret = getSecret();
  } catch {
    return false;
  }
  const expected = await hmacHex(secret, expiryStr);
  return safeEqual(mac, expected);
}
