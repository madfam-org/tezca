import { describe, it, expect, vi, beforeEach } from 'vitest';

interface MockResponse {
    status: number;
    body: { error?: string; access_token?: string };
}

// Mock next/server
vi.mock('next/server', () => ({
    NextResponse: {
        json: (body: unknown, init?: { status?: number }) => ({
            body,
            status: init?.status ?? 200,
        }),
    },
}));

// Mock next/headers
vi.mock('next/headers', () => ({
    cookies: vi.fn(() => Promise.resolve({
        set: vi.fn(),
    })),
}));

// Mock jose
vi.mock('jose', () => ({
    SignJWT: vi.fn(() => ({
        setProtectedHeader: vi.fn().mockReturnThis(),
        setIssuedAt: vi.fn().mockReturnThis(),
        setExpirationTime: vi.fn().mockReturnThis(),
        sign: vi.fn().mockResolvedValue('mock.jwt.token'),
    })),
}));

describe('POST /api/auth/login', () => {
    const originalFetch = globalThis.fetch;

    beforeEach(() => {
        vi.resetModules();
        globalThis.fetch = originalFetch;
    });

    async function importAndCall(body: object) {
        const { POST } = await import('@/app/api/auth/login/route');
        const request = new Request('http://localhost/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return POST(request);
    }

    it('returns 400 when email is missing', async () => {
        const res = await importAndCall({ password: 'secret' }) as MockResponse;
        expect(res.status).toBe(400);
        expect(res.body.error).toMatch(/Correo y contraseña/);
    });

    it('returns 400 when password is missing', async () => {
        const res = await importAndCall({ email: 'a@b.com' }) as MockResponse;
        expect(res.status).toBe(400);
        expect(res.body.error).toMatch(/Correo y contraseña/);
    });

    it('returns 503 when upstream returns HTML instead of JSON', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce(
            new Response('<!DOCTYPE html><html>Cloudflare challenge</html>', {
                status: 200,
                headers: { 'Content-Type': 'text/html' },
            })
        );

        const res = await importAndCall({ email: 'a@b.com', password: 'p' }) as MockResponse;
        expect(res.status).toBe(503);
        expect(res.body.error).toMatch(/no está disponible/);
    });

    it('returns upstream error status on non-OK JSON response', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce(
            new Response(JSON.stringify({ detail: 'Cuenta bloqueada' }), {
                status: 403,
                headers: { 'Content-Type': 'application/json' },
            })
        );

        const res = await importAndCall({ email: 'a@b.com', password: 'p' }) as MockResponse;
        expect(res.status).toBe(403);
        expect(res.body.error).toBe('Cuenta bloqueada');
    });

    it('returns 502 on network failure', async () => {
        globalThis.fetch = vi.fn().mockRejectedValueOnce(new Error('ECONNREFUSED'));

        const res = await importAndCall({ email: 'a@b.com', password: 'p' }) as MockResponse;
        expect(res.status).toBe(502);
        expect(res.body.error).toMatch(/Error de conexión/);
    });
});
