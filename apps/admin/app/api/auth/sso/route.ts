import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const JANUA_BASE_URL = process.env.NEXT_PUBLIC_JANUA_BASE_URL || "https://auth.madfam.io";
const CLIENT_ID = process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || "";

export async function GET(request: Request) {
    if (!CLIENT_ID) {
        return NextResponse.json({ error: "Janua not configured" }, { status: 503 });
    }

    const origin = new URL(request.url).origin;
    const redirectUri = `${origin}/api/auth/callback`;

    // Generate state for CSRF protection
    const state = crypto.randomUUID();

    // Store state in a short-lived cookie
    const cookieStore = await cookies();
    cookieStore.set("janua-oauth-state", state, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 300, // 5 minutes
    });

    const params = new URLSearchParams({
        client_id: CLIENT_ID,
        redirect_uri: redirectUri,
        response_type: "code",
        scope: "openid profile email",
        state,
    });

    return NextResponse.redirect(
        `${JANUA_BASE_URL}/api/v1/oauth/authorize?${params.toString()}`
    );
}
