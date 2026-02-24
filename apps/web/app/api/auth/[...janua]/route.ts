import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { jwtVerify } from 'jose';

const JWT_SECRET = process.env.JANUA_SECRET_KEY || '';

export async function GET(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // GET /api/auth/session — return current session from cookie
  if (pathname.endsWith('/session')) {
    try {
      const cookieStore = await cookies();
      const token = cookieStore.get('janua-session')?.value;
      if (!token || !JWT_SECRET) {
        return NextResponse.json({ user: null });
      }
      const { payload } = await jwtVerify(
        token,
        new TextEncoder().encode(JWT_SECRET),
      );
      return NextResponse.json({
        user: {
          id: payload.sub,
          email: payload.email,
          name: payload.name,
          tier: payload.tier ?? 'free',
        },
      });
    } catch {
      return NextResponse.json({ user: null });
    }
  }

  return NextResponse.json({ error: 'Not found' }, { status: 404 });
}

export async function POST(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // POST /api/auth/signout — clear session cookie
  if (pathname.endsWith('/signout')) {
    const cookieStore = await cookies();
    cookieStore.delete('janua-session');
    return NextResponse.json({ success: true });
  }

  return NextResponse.json({ error: 'Not found' }, { status: 404 });
}
