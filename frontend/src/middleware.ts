import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const url = req.nextUrl.clone();
  const hostname = (req.headers.get("host") || "").split(":")[0].toLowerCase();

  const redirectTo = (host: string, pathname: string) => {
    url.hostname = host;
    url.pathname = pathname;
    return NextResponse.redirect(url);
  };

  if (hostname === "creator.squarecloudsmc.com") {
    if (url.pathname === "/") {
      url.pathname = "/login";
      return NextResponse.rewrite(url);
    }

    if (["/login", "/admin", "/creator"].includes(url.pathname)) {
      return NextResponse.next();
    }

    if (url.pathname === "/admin-cms") {
      return redirectTo("access.squarecloudsmc.com", "/login");
    }

    return NextResponse.next();
  }

  if (hostname === "access.squarecloudsmc.com") {
    if (url.pathname === "/") {
      url.pathname = "/login";
      return NextResponse.rewrite(url);
    }

    if (["/login", "/admin-cms"].includes(url.pathname)) {
      return NextResponse.next();
    }

    if (["/admin", "/creator"].includes(url.pathname)) {
      return redirectTo("access.squarecloudsmc.com", "/login");
    }

    return NextResponse.next();
  }

  if (
    (hostname === "squarecloudsmc.com" || hostname === "www.squarecloudsmc.com") &&
    ["/login", "/admin", "/creator", "/admin-cms"].includes(url.pathname)
  ) {
    return redirectTo(hostname, "/");
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico*\\..*).*)"],
};
