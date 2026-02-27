import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { createJanuaMiddleware } from "@janua/nextjs/middleware";

const jwtSecret = process.env.JANUA_SECRET_KEY || "";
const isProduction = process.env.NODE_ENV === "production";

// When no secret key is configured:
// - Production: return 503 (auth required but not configured)
// - Dev mode: all routes are open (passthrough)
const januaMiddleware = jwtSecret
    ? createJanuaMiddleware({
          jwtSecret,
          publicRoutes: ["/sign-in", "/api/health", "/api/auth/*"],
          redirectUrl: "/sign-in",
      })
    : null;

export default function middleware(req: NextRequest) {
    if (!januaMiddleware) {
        if (isProduction) {
            return new NextResponse(
                "Admin panel unavailable: authentication not configured",
                { status: 503 }
            );
        }
        return NextResponse.next();
    }
    return januaMiddleware(req);
}

export const config = {
    matcher: [
        "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    ],
};
