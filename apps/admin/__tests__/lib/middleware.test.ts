import { NextRequest } from 'next/server';
import { middleware } from '@/middleware';

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

describe('middleware', () => {
    it('allows public paths without session', () => {
        const paths = ['/sign-in', '/api/auth/callback', '/_next/data', '/favicon.ico', '/icon.svg'];
        for (const path of paths) {
            const response = middleware(createRequest(path));
            expect(response.status).not.toBe(307);
        }
    });

    it('redirects to /sign-in when no session cookie', () => {
        const response = middleware(createRequest('/metrics'));
        expect(response.status).toBe(307);
        expect(new URL(response.headers.get('location')!).pathname).toBe('/sign-in');
    });

    it('allows access when janua-session cookie is present', () => {
        const response = middleware(createRequest('/metrics', { 'janua-session': 'valid-session' }));
        expect(response.status).toBe(200);
    });

    it('redirects protected pages without session', () => {
        const protectedPaths = ['/metrics', '/dataops', '/ingestion', '/roadmap', '/settings', '/'];
        for (const path of protectedPaths) {
            const response = middleware(createRequest(path));
            expect(response.status).toBe(307);
        }
    });
});
