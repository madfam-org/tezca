import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { SignJWT } from "jose";

const JANUA_ISSUER_URL =
    process.env.NEXT_PUBLIC_JANUA_ISSUER_URL ||
    process.env.NEXT_PUBLIC_JANUA_BASE_URL ||
    "https://auth.madfam.io";
const JANUA_SERVER_URL = process.env.JANUA_INTERNAL_URL || JANUA_ISSUER_URL;
const CLIENT_ID = process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || "";
const CLIENT_SECRET = process.env.JANUA_SECRET_KEY || "";

function getOrigin(request: Request): string {
    const h = new Headers(request.headers);
    const host = h.get("x-forwarded-host") || h.get("host") || new URL(request.url).host;
    const proto = h.get("x-forwarded-proto") || "https";
    return `${proto}://${host}`;
}

/**
 * GET /api/auth/callback — OAuth 2.0 Authorization Code callback with PKCE.
 *
 * Creates a janua-session cookie compatible with @janua/nextjs middleware.
 */
export async function GET(request: Request) {
    const url = new URL(request.url);
    const origin = getOrigin(request);
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const error = url.searchParams.get("error");

    if (error) {
        const desc = url.searchParams.get("error_description") || error;
        return NextResponse.redirect(
            `${origin}/sign-in?sso_error=${encodeURIComponent(desc)}`
        );
    }

    if (!code || !state) {
        return NextResponse.redirect(
            `${origin}/sign-in?sso_error=${encodeURIComponent("Respuesta de autenticacion incompleta")}`
        );
    }

    const cookieStore = await cookies();
    const storedState = cookieStore.get("janua-oauth-state")?.value;
    const codeVerifier = cookieStore.get("janua-pkce-verifier")?.value;
    cookieStore.delete("janua-oauth-state");
    cookieStore.delete("janua-pkce-verifier");

    if (!storedState || storedState !== state) {
        return NextResponse.redirect(
            `${origin}/sign-in?sso_error=${encodeURIComponent("Estado de sesion invalido. Intenta de nuevo.")}`
        );
    }

    // Exchange authorization code for tokens
    const redirectUri = `${origin}/api/auth/callback`;
    let tokenData: {
        access_token: string;
        refresh_token?: string;
        expires_in?: number;
    };

    try {
        const tokenRes = await fetch(`${JANUA_SERVER_URL}/api/v1/oauth/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                grant_type: "authorization_code",
                code,
                redirect_uri: redirectUri,
                client_id: CLIENT_ID,
                client_secret: CLIENT_SECRET,
                ...(codeVerifier ? { code_verifier: codeVerifier } : {}),
            }),
        });

        if (!tokenRes.ok) {
            const body = await tokenRes.text();
            console.error("Token exchange failed:", tokenRes.status, body);
            return NextResponse.redirect(
                `${origin}/sign-in?sso_error=${encodeURIComponent("Error al intercambiar codigo de autorizacion")}`
            );
        }

        tokenData = await tokenRes.json();
    } catch (err) {
        console.error("Token exchange error:", err);
        return NextResponse.redirect(
            `${origin}/sign-in?sso_error=${encodeURIComponent("Error de conexion con el servidor de autenticacion")}`
        );
    }

    // Fetch user info
    let userInfo: {
        sub?: string;
        email?: string;
        given_name?: string;
        family_name?: string;
        email_verified?: boolean;
        picture?: string;
    } | null = null;

    try {
        const userRes = await fetch(`${JANUA_SERVER_URL}/api/v1/oauth/userinfo`, {
            headers: { Authorization: `Bearer ${tokenData.access_token}` },
        });
        if (userRes.ok) {
            userInfo = await userRes.json();
        }
    } catch {
        // userinfo is optional
    }

    // Build session data matching @janua/nextjs JanuaServerClient format
    const expiresIn = tokenData.expires_in || 3600;
    const sessionData = {
        user: userInfo
            ? {
                  id: userInfo.sub,
                  email: userInfo.email,
                  first_name: userInfo.given_name || null,
                  last_name: userInfo.family_name || null,
                  email_verified: userInfo.email_verified || false,
                  profile_image_url: userInfo.picture || null,
              }
            : { id: "unknown", email: "unknown" },
        session: {
            id: "oidc-" + crypto.randomUUID(),
            user_id: userInfo?.sub || "unknown",
            is_current: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + expiresIn * 1000).toISOString(),
            last_activity: new Date().toISOString(),
        },
        accessToken: tokenData.access_token,
        refreshToken: tokenData.refresh_token,
    };

    // Sign session JWT (HS256, 7d TTL) — same format as @janua/nextjs middleware expects
    const secret = new TextEncoder().encode(CLIENT_SECRET);
    const sessionJwt = await new SignJWT({ data: sessionData })
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("7d")
        .sign(secret);

    cookieStore.set("janua-session", sessionJwt, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 24 * 7,
    });

    // Token bridge for client-side SDK hydration (short-lived, JS-readable)
    const tokenBridge = JSON.stringify({
        access_token: tokenData.access_token,
        refresh_token: tokenData.refresh_token || "",
        expires_at: Math.floor(Date.now() / 1000 + expiresIn),
    });
    cookieStore.set("janua-sso-tokens", tokenBridge, {
        httpOnly: false,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 60,
    });

    return NextResponse.redirect(`${origin}/`);
}
