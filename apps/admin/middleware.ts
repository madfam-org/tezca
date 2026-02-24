import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { createJanuaMiddleware } from "@janua/nextjs/middleware";

const jwtSecret = process.env.JANUA_SECRET_KEY || "";

// When no secret key is configured, all routes are open (dev mode)
const januaMiddleware = jwtSecret
    ? createJanuaMiddleware({
          jwtSecret,
          publicRoutes: ["/sign-in", "/api/health"],
          redirectUrl: "/sign-in",
      })
    : null;

export default function middleware(req: NextRequest) {
    if (!januaMiddleware) {
        return NextResponse.next();
    }
    return januaMiddleware(req);
}

export const config = {
    matcher: [
        "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    ],
};
