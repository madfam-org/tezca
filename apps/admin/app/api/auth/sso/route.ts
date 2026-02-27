import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const JANUA_BASE_URL = process.env.NEXT_PUBLIC_JANUA_BASE_URL || "https://auth.madfam.io";
const CLIENT_ID = process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || "";

function getOrigin(request: Request): string {
    const h = new Headers(request.headers);
    const host = h.get("x-forwarded-host") || h.get("host") || new URL(request.url).host;
    const proto = h.get("x-forwarded-proto") || "https";
    return `${proto}://${host}`;
}

function generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return base64UrlEncode(array);
}

async function generateCodeChallenge(verifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest("SHA-256", data);
    return base64UrlEncode(new Uint8Array(digest));
}

function base64UrlEncode(buffer: Uint8Array): string {
    let binary = "";
    for (const byte of buffer) {
        binary += String.fromCharCode(byte);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function GET(request: Request) {
    if (!CLIENT_ID) {
        return NextResponse.json({ error: "Janua not configured" }, { status: 503 });
    }

    const origin = getOrigin(request);
    const redirectUri = `${origin}/api/auth/callback`;

    // Generate state for CSRF protection
    const state = crypto.randomUUID();

    // Generate PKCE code verifier and challenge
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);

    // Store state and code_verifier in short-lived cookies
    const cookieStore = await cookies();
    cookieStore.set("janua-oauth-state", state, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 300, // 5 minutes
    });
    cookieStore.set("janua-pkce-verifier", codeVerifier, {
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
        code_challenge: codeChallenge,
        code_challenge_method: "S256",
    });

    return NextResponse.redirect(
        `${JANUA_BASE_URL}/api/v1/oauth/authorize?${params.toString()}`
    );
}
