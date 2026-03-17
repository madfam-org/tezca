import { api, APIError } from '@/lib/api';

describe('API client', () => {
    const originalFetch = global.fetch;

    afterEach(() => {
        global.fetch = originalFetch;
        vi.restoreAllMocks();
    });

    function mockFetch(response: Partial<Response>) {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: () => Promise.resolve({}),
            ...response,
        });
    }

    describe('fetcher', () => {
        it('includes credentials and JSON content-type', async () => {
            mockFetch({ json: () => Promise.resolve({ ok: true }) });
            await api.getHealth();

            expect(fetch).toHaveBeenCalledWith(
                expect.any(String),
                expect.objectContaining({
                    credentials: 'include',
                    headers: expect.objectContaining({
                        'Content-Type': 'application/json',
                    }),
                }),
            );
        });

        it('throws APIError on non-ok response', async () => {
            mockFetch({ ok: false, status: 404, statusText: 'Not Found' });
            await expect(api.getMetrics()).rejects.toThrow('API request failed');
            await expect(api.getMetrics()).rejects.toBeInstanceOf(APIError);
        });

        it('wraps network errors in APIError', async () => {
            global.fetch = vi.fn().mockRejectedValue(new Error('Connection refused'));
            await expect(api.getConfig()).rejects.toThrow('Network error');
        });

        it('redirects to /sign-in on 401 and clears stale tokens', async () => {
            mockFetch({ ok: false, status: 401, statusText: 'Unauthorized' });

            const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem');

            const result = await Promise.race([
                api.getHealth().then(() => 'resolved').catch(() => 'rejected'),
                new Promise<string>((r) => setTimeout(() => r('pending'), 50)),
            ]);

            expect(result).toBe('pending');
            expect(removeItemSpy).toHaveBeenCalledWith('janua_access_token');
            expect(removeItemSpy).toHaveBeenCalledWith('janua_refresh_token');
            expect(removeItemSpy).toHaveBeenCalledWith('janua_token_expires_at');

            removeItemSpy.mockRestore();
        });
    });

    describe('endpoints', () => {
        it('GET /admin/metrics/', async () => {
            const metrics = { total_laws: 500 };
            mockFetch({ json: () => Promise.resolve(metrics) });
            const result = await api.getMetrics();
            expect(result).toEqual(metrics);
            expect(fetch).toHaveBeenCalledWith(
                expect.stringContaining('/admin/metrics/'),
                expect.any(Object),
            );
        });

        it('GET /admin/config/', async () => {
            mockFetch({ json: () => Promise.resolve({ environment: {} }) });
            await api.getConfig();
            expect(fetch).toHaveBeenCalledWith(
                expect.stringContaining('/admin/config/'),
                expect.any(Object),
            );
        });

        it('GET /admin/health/', async () => {
            mockFetch({ json: () => Promise.resolve({ status: 'healthy' }) });
            await api.getHealth();
            expect(fetch).toHaveBeenCalledWith(
                expect.stringContaining('/admin/health/'),
                expect.any(Object),
            );
        });

        it('POST /ingest/ with body', async () => {
            mockFetch({ json: () => Promise.resolve({ status: 'running' }) });
            await api.startIngestion({ mode: 'all' });
            expect(fetch).toHaveBeenCalledWith(
                expect.stringContaining('/ingest/'),
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({ mode: 'all' }),
                }),
            );
        });

        it('PATCH /admin/roadmap/ with body', async () => {
            mockFetch({ json: () => Promise.resolve({ ok: true, id: 1, status: 'completed', progress_pct: 100 }) });
            await api.updateRoadmapItem({ id: 1, status: 'completed' });
            expect(fetch).toHaveBeenCalledWith(
                expect.stringContaining('/admin/roadmap/'),
                expect.objectContaining({
                    method: 'PATCH',
                    body: JSON.stringify({ id: 1, status: 'completed' }),
                }),
            );
        });
    });
});
