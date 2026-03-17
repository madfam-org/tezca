import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Public paths that do not require a janua-session cookie.
 * Everything else redirects unauthenticated users to /sign-in.
 */
const PUBLIC_PATHS = [
    "/sign-in",
    "/api/auth",     // /api/auth/sso, /api/auth/callback, /api/auth/login, /api/auth/me
    "/api/v1/auth",  // /api/v1/auth/login proxy used by @janua/ui SignIn component
    "/_next",
    "/favicon.ico",
    "/icon",
];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Allow public paths through without authentication
    if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
        return NextResponse.next();
    }

    // Require janua-session cookie for all other routes
    const session = request.cookies.get("janua-session");
    if (!session?.value) {
        const signInUrl = new URL("/sign-in", request.url);
        return NextResponse.redirect(signInUrl);
    }

    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
