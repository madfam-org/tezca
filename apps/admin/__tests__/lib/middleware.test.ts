import { NextRequest, NextResponse } from 'next/server';

// Mock jose to control JWT verification
vi.mock('jose', () => ({
    jwtVerify: vi.fn(),
}));

import { jwtVerify } from 'jose';

// Import the middleware after mocks
const { default: middleware } = await import('@/middleware');

function createRequest(pathname: string, cookies?: Record<string, string>) {
    const url = new URL(pathname, 'http://localhost:3000');
    const req = new NextRequest(url);
    if (cookies) {
        for (const [name, value] of Object.entries(cookies)) {
            req.cookies.set(name, value);
        }
    }
    return req;
}

describe('createJanuaMiddleware', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('allows public paths without session', async () => {
        const paths = ['/sign-in', '/api/auth/callback', '/api/auth/sso', '/api/health'];
        for (const path of paths) {
            const response = await middleware(createRequest(path));
            expect(response.status).not.toBe(307);
        }
    });

    it('redirects to /sign-in when no session cookie', async () => {
        const response = await middleware(createRequest('/metrics'));
        expect(response.status).toBe(307);
        expect(new URL(response.headers.get('location')!).pathname).toBe('/sign-in');
    });

    it('allows access when janua-session cookie has valid JWT', async () => {
        (jwtVerify as ReturnType<typeof vi.fn>).mockResolvedValue({
            payload: { data: { user: { id: '1' } } },
        });
        const response = await middleware(createRequest('/metrics', { 'janua-session': 'valid.jwt.token' }));
        expect(response.status).toBe(200);
    });

    it('redirects when janua-session cookie has invalid JWT', async () => {
        (jwtVerify as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('invalid'));
        const response = await middleware(createRequest('/metrics', { 'janua-session': 'bad-token' }));
        expect(response.status).toBe(307);
        expect(new URL(response.headers.get('location')!).pathname).toBe('/sign-in');
    });

    it('redirects protected pages without session', async () => {
        const protectedPaths = ['/metrics', '/dataops', '/ingestion', '/roadmap', '/settings', '/'];
        for (const path of protectedPaths) {
            const response = await middleware(createRequest(path));
            expect(response.status).toBe(307);
        }
    });
});
