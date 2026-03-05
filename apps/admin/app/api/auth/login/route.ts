import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { SignJWT } from "jose";

const JANUA_BASE_URL =
    process.env.NEXT_PUBLIC_JANUA_BASE_URL || "https://auth.madfam.io";
const CLIENT_SECRET = process.env.JANUA_SECRET_KEY || "";

/**
 * POST /api/auth/login — server-side proxy for email/password login.
 *
 * Avoids CORS by proxying the Janua login call from the server instead
 * of making a direct browser XHR to auth.madfam.io.
 */
export async function POST(request: Request) {
    let body: { email?: string; password?: string };
    try {
        body = await request.json();
    } catch {
        return NextResponse.json(
            { error: "Cuerpo de solicitud inválido" },
            { status: 400 }
        );
    }

    const { email, password } = body;
    if (!email || !password) {
        return NextResponse.json(
            { error: "Correo y contraseña son requeridos" },
            { status: 400 }
        );
    }

    // Proxy to Janua's login endpoint server-side
    let loginData;
    try {
        const loginRes = await fetch(
            `${JANUA_BASE_URL}/api/v1/auth/login`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            }
        );

        if (!loginRes.ok) {
            const errBody = await loginRes.text();
            let message = "Credenciales inválidas";
            try {
                const parsed = JSON.parse(errBody);
                if (parsed.detail) message = parsed.detail;
                else if (parsed.message) message = parsed.message;
                else if (parsed.error) message = parsed.error;
            } catch {
                // use default message
            }
            return NextResponse.json(
                { error: message },
                { status: loginRes.status }
            );
        }

        loginData = await loginRes.json();
    } catch (err) {
        console.error("Login proxy error:", err);
        return NextResponse.json(
            { error: "Error de conexión con el servidor de autenticación" },
            { status: 502 }
        );
    }

    const accessToken =
        loginData.access_token || loginData.token || loginData.accessToken;
    const refreshToken =
        loginData.refresh_token || loginData.refreshToken || "";
    const expiresIn = loginData.expires_in || 3600;

    if (!accessToken) {
        return NextResponse.json(
            { error: "Respuesta inesperada del servidor de autenticación" },
            { status: 502 }
        );
    }

    // Fetch user info from Janua
    let userInfo;
    try {
        const userRes = await fetch(`${JANUA_BASE_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (userRes.ok) {
            userInfo = await userRes.json();
        }
    } catch {
        // user info is optional, continue without it
    }

    // Build session data matching callback route format
    const user = userInfo?.user || userInfo;
    const sessionData = {
        user: user
            ? {
                  id: user.id || user.sub || "unknown",
                  email: user.email || email,
                  first_name: user.first_name || user.given_name || null,
                  last_name: user.last_name || user.family_name || null,
                  email_verified: user.email_verified || false,
                  profile_image_url:
                      user.profile_image_url || user.picture || null,
              }
            : { id: "unknown", email },
        session: {
            id: "login-" + crypto.randomUUID(),
            user_id: user?.id || user?.sub || "unknown",
            is_current: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            expires_at: new Date(
                Date.now() + expiresIn * 1000
            ).toISOString(),
            last_activity: new Date().toISOString(),
        },
        accessToken,
        refreshToken,
    };

    // Create janua-session cookie (HS256 JWT, same as callback route)
    const secret = new TextEncoder().encode(CLIENT_SECRET);
    const sessionJwt = await new SignJWT({ data: sessionData })
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("7d")
        .sign(secret);

    const cookieStore = await cookies();
    cookieStore.set("janua-session", sessionJwt, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    // Return tokens for client-side SDK hydration
    return NextResponse.json({
        access_token: accessToken,
        refresh_token: refreshToken,
        expires_at: Math.floor(Date.now() / 1000 + expiresIn),
        user: sessionData.user,
    });
}
