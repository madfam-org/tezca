import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { jwtVerify } from "jose";

const CLIENT_SECRET = process.env.JANUA_SECRET_KEY || "";

/**
 * GET /api/auth/me — server-side session check.
 *
 * Reads the janua-session cookie and validates it locally (HS256),
 * avoiding a browser XHR to auth.madfam.io that would fail with CORS.
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

    if (!CLIENT_SECRET) {
        return NextResponse.json(
            { authenticated: false, error: "Server not configured" },
            { status: 500 }
        );
    }

    try {
        const secret = new TextEncoder().encode(CLIENT_SECRET);
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
