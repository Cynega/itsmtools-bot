import { NextResponse, type NextRequest } from "next/server";
import { sign, safeEqual, AUTH_COOKIE, AUTH_MAX_AGE } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const expected = process.env.APP_PASSWORD;
  if (!expected) {
    return NextResponse.json({ error: "server misconfigured" }, { status: 500 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid body" }, { status: 400 });
  }
  const password =
    body && typeof body === "object" && "password" in body
      ? (body as { password: unknown }).password
      : undefined;

  if (typeof password !== "string" || !safeEqual(password, expected)) {
    return NextResponse.json({ error: "invalid password" }, { status: 401 });
  }

  const token = await sign(AUTH_MAX_AGE);
  const res = NextResponse.json({ ok: true });
  res.cookies.set(AUTH_COOKIE, token, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
    maxAge: AUTH_MAX_AGE,
  });
  return res;
}
