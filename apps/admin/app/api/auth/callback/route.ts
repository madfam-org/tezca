import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { SignJWT } from "jose";

const JANUA_BASE_URL = process.env.NEXT_PUBLIC_JANUA_BASE_URL || "https://auth.madfam.io";
const CLIENT_ID = process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || "";
const CLIENT_SECRET = process.env.JANUA_SECRET_KEY || "";

export async function GET(request: Request) {
    const url = new URL(request.url);
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const error = url.searchParams.get("error");

    if (error) {
        const desc = url.searchParams.get("error_description") || error;
        return NextResponse.redirect(
            `${url.origin}/sign-in?sso_error=${encodeURIComponent(desc)}`
        );
    }

    if (!code || !state) {
        return NextResponse.redirect(
            `${url.origin}/sign-in?sso_error=${encodeURIComponent("Respuesta de autenticación incompleta")}`
        );
    }

    // Validate state
    const cookieStore = await cookies();
    const storedState = cookieStore.get("janua-oauth-state")?.value;
    cookieStore.delete("janua-oauth-state");

    if (!storedState || storedState !== state) {
        return NextResponse.redirect(
            `${url.origin}/sign-in?sso_error=${encodeURIComponent("Estado de sesión inválido. Intenta de nuevo.")}`
        );
    }

    // Exchange authorization code for tokens
    const redirectUri = `${url.origin}/api/auth/callback`;
    let tokenData;
    try {
        const tokenRes = await fetch(`${JANUA_BASE_URL}/api/v1/oauth/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                grant_type: "authorization_code",
                code,
                redirect_uri: redirectUri,
                client_id: CLIENT_ID,
                client_secret: CLIENT_SECRET,
            }),
        });

        if (!tokenRes.ok) {
            const body = await tokenRes.text();
            console.error("Token exchange failed:", tokenRes.status, body);
            return NextResponse.redirect(
                `${url.origin}/sign-in?sso_error=${encodeURIComponent("Error al intercambiar código de autorización")}`
            );
        }

        tokenData = await tokenRes.json();
    } catch (err) {
        console.error("Token exchange error:", err);
        return NextResponse.redirect(
            `${url.origin}/sign-in?sso_error=${encodeURIComponent("Error de conexión con el servidor de autenticación")}`
        );
    }

    // Fetch user info
    let userInfo;
    try {
        const userRes = await fetch(`${JANUA_BASE_URL}/api/v1/oauth/userinfo`, {
            headers: { Authorization: `Bearer ${tokenData.access_token}` },
        });

        if (userRes.ok) {
            userInfo = await userRes.json();
        }
    } catch {
        // userinfo is optional, continue without it
    }

    // Build session data matching JanuaServerClient format
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
            expires_at: new Date(
                Date.now() + (tokenData.expires_in || 3600) * 1000
            ).toISOString(),
            last_activity: new Date().toISOString(),
        },
        accessToken: tokenData.access_token,
        refreshToken: tokenData.refresh_token,
    };

    // Create janua-session cookie (HS256 JWT matching middleware expectations)
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
        maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    // Set tokens in a JS-readable cookie for client-side SDK hydration.
    // Short-lived (60s) — the client reads and deletes it immediately.
    const tokenBridge = JSON.stringify({
        access_token: tokenData.access_token,
        refresh_token: tokenData.refresh_token || "",
        expires_at: Math.floor(
            Date.now() / 1000 + (tokenData.expires_in || 3600)
        ),
    });
    cookieStore.set("janua-sso-tokens", tokenBridge, {
        httpOnly: false, // must be readable by client JS
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 60,
    });

    return NextResponse.redirect(`${url.origin}/`);
}
