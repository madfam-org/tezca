import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { jwtVerify } from "jose";

const JANUA_SECRET_KEY = process.env.JANUA_SECRET_KEY || "";

/**
 * GET /api/auth/me — server-side session check.
 *
 * Reads the janua-session cookie, verifies the HS256 JWT locally,
 * and returns the authenticated user info for client-side hydration.
 *
 * Uses the same cookie format as @janua/nextjs JanuaServerClient.
 */
export async function GET() {
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("janua-session")?.value;

    if (!sessionCookie) {
        return NextResponse.json(
            { authenticated: false },
            { status: 401 }
        );
    }

    if (!JANUA_SECRET_KEY) {
        return NextResponse.json(
            { authenticated: false, error: "Server not configured" },
            { status: 500 }
        );
    }

    try {
        const secret = new TextEncoder().encode(JANUA_SECRET_KEY);
        const { payload } = await jwtVerify(sessionCookie, secret);
        const data = payload.data as {
            user: {
                id: string;
                email: string;
                first_name?: string | null;
                last_name?: string | null;
                email_verified?: boolean;
                profile_image_url?: string | null;
            };
            session: {
                id: string;
                expires_at: string;
            };
            accessToken: string;
            refreshToken?: string;
        };

        if (!data?.user || !data?.accessToken) {
            return NextResponse.json(
                { authenticated: false },
                { status: 401 }
            );
        }

        // Check session expiry
        const expiresAt = new Date(data.session.expires_at).getTime();
        if (expiresAt < Date.now()) {
            return NextResponse.json(
                { authenticated: false, reason: "expired" },
                { status: 401 }
            );
        }

        return NextResponse.json({
            authenticated: true,
            user: data.user,
            access_token: data.accessToken,
            refresh_token: data.refreshToken || "",
            expires_at: Math.floor(expiresAt / 1000),
        });
    } catch {
        return NextResponse.json(
            { authenticated: false },
            { status: 401 }
        );
    }
}
