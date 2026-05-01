import { NextResponse, type NextRequest } from "next/server";
import { verify, AUTH_COOKIE } from "@/lib/auth";

export const config = {
  matcher: [
    // Todas las rutas excepto: assets de Next, /login, endpoints de auth,
    // robots.txt y favicon. /api/generate (Python) NO entra acá porque
    // Vercel lo rutea directo a la function — ese endpoint valida su
    // propia cookie en api/generate.py.
    "/((?!_next/|login|api/auth/|robots\\.txt|favicon\\.ico).*)",
  ],
};

export async function proxy(req: NextRequest) {
  const token = req.cookies.get(AUTH_COOKIE)?.value;
  if (await verify(token)) {
    return NextResponse.next();
  }
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  return NextResponse.redirect(url);
}
