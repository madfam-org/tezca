import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

let middleware: (req: NextRequest) => ReturnType<typeof NextResponse.next>;
let januaAvailable = false;

try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { createJanuaMiddleware } = require("@janua/nextjs/middleware");
    middleware = createJanuaMiddleware({
        jwtSecret: process.env.JANUA_SECRET_KEY || '',
        publicRoutes: ["/sign-in", "/api/health"],
        redirectUrl: "/sign-in",
    });
    januaAvailable = true;
} catch {
    // @janua/nextjs not installed — redirect non-public routes to setup notice
    middleware = (req: NextRequest) => {
        const { pathname } = req.nextUrl;
        // Allow health check and static assets through
        if (pathname === "/api/health" || pathname === "/sign-in") {
            return NextResponse.next();
        }
        // Redirect to sign-in which shows the "auth not configured" message
        const signInUrl = new URL("/sign-in", req.url);
        return NextResponse.redirect(signInUrl);
    };
}

export default function handler(req: NextRequest) {
    return middleware(req);
}

export const config = {
    matcher: [
        "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    ],
};

export { januaAvailable };
