import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(req: NextRequest) {
  const tieneSesion = req.cookies.has("ct_sesion");
  if (!tieneSesion) {
    return NextResponse.redirect(new URL("/entrar", req.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/panel/:path*", "/panel", "/mi-unidad", "/reglamento"] };
