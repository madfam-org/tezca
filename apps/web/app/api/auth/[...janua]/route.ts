import { NextRequest, NextResponse } from 'next/server';
import { JanuaServerClient } from '@janua/nextjs';

const janua = new JanuaServerClient({
  appId: process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || '',
  apiKey: process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || '',
  jwtSecret: process.env.JANUA_SECRET_KEY || '',
});

export async function GET(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // GET /api/auth/session — return current session
  if (pathname.endsWith('/session')) {
    const session = await janua.getSession();
    return NextResponse.json(session ?? { user: null });
  }

  return NextResponse.json({ error: 'Not found' }, { status: 404 });
}

export async function POST(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // POST /api/auth/signout — clear session
  if (pathname.endsWith('/signout')) {
    await janua.signOut();
    return NextResponse.json({ success: true });
  }

  return NextResponse.json({ error: 'Not found' }, { status: 404 });
}
