import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('config', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        vi.resetModules();
    });

    afterEach(() => {
        process.env = originalEnv;
    });

    it('uses default API_BASE_URL when env var is not set', async () => {
        process.env = { ...originalEnv };
        delete process.env.NEXT_PUBLIC_API_URL;
        delete process.env.INTERNAL_API_URL;

        const { API_BASE_URL, INTERNAL_API_URL } = await import('@/lib/config');
        expect(API_BASE_URL).toBe('http://localhost:8000/api/v1');
        expect(INTERNAL_API_URL).toBe(API_BASE_URL);
    });

    it('respects NEXT_PUBLIC_API_URL env var', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_API_URL: 'https://api.tezca.mx/api/v1' };
        delete process.env.INTERNAL_API_URL;

        const { API_BASE_URL, INTERNAL_API_URL } = await import('@/lib/config');
        expect(API_BASE_URL).toBe('https://api.tezca.mx/api/v1');
        expect(INTERNAL_API_URL).toBe('https://api.tezca.mx/api/v1');
    });
});
