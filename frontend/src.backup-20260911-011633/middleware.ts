import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const url = req.nextUrl.clone();
  const hostname = req.headers.get("host") || "";

  // Jika diakses via subdomain creator (misal: creator.squarecloudsmc.com)
  if (hostname.startsWith("creator.")) {
    if (url.pathname === "/") {
      url.pathname = "/login"; // Atau arahkan ke halaman admin/portal
    }
    return NextResponse.rewrite(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.png|logo.png|.*\\..*).*)"],
};
