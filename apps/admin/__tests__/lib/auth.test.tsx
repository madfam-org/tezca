import { render, renderHook } from '@testing-library/react';
import { setTokenSource, api, APIError } from '@/lib/api';

// Mock @janua/nextjs since it's not installed in test env
vi.mock('@janua/nextjs', () => ({
    JanuaProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    UserButton: () => <div data-testid="user-button" />,
    SignInForm: ({ redirectTo }: { redirectTo: string }) => <div data-testid="sign-in-form" data-redirect={redirectTo} />,
    useJanua: vi.fn(() => ({
        client: null,
        user: null,
        isLoading: false,
        isAuthenticated: false,
        signOut: vi.fn(),
    })),
}));

describe('setTokenSource + fetcher integration', () => {
    const originalFetch = global.fetch;

    afterEach(() => {
        global.fetch = originalFetch;
        setTokenSource(null);
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

    it('sends no Authorization header when token source is null', async () => {
        mockFetch({ json: () => Promise.resolve({ status: 'healthy' }) });
        setTokenSource(null);
        await api.getHealth();

        const callHeaders = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
        expect(callHeaders).not.toHaveProperty('Authorization');
    });

    it('sends Authorization header when token source returns a token', async () => {
        mockFetch({ json: () => Promise.resolve({ status: 'healthy' }) });
        setTokenSource(() => Promise.resolve('test-jwt-token'));
        await api.getHealth();

        const callHeaders = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
        expect(callHeaders['Authorization']).toBe('Bearer test-jwt-token');
    });

    it('sends no Authorization header when token source returns null', async () => {
        mockFetch({ json: () => Promise.resolve({ status: 'healthy' }) });
        setTokenSource(() => Promise.resolve(null));
        await api.getHealth();

        const callHeaders = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
        expect(callHeaders).not.toHaveProperty('Authorization');
    });

    it('retries with fresh token on 401', async () => {
        let callCount = 0;
        global.fetch = vi.fn().mockImplementation(() => {
            callCount++;
            if (callCount === 1) {
                return Promise.resolve({
                    ok: false,
                    status: 401,
                    statusText: 'Unauthorized',
                    json: () => Promise.resolve({}),
                });
            }
            return Promise.resolve({
                ok: true,
                status: 200,
                json: () => Promise.resolve({ status: 'healthy' }),
            });
        });

        let tokenCallCount = 0;
        setTokenSource(() => {
            tokenCallCount++;
            return Promise.resolve(tokenCallCount === 1 ? 'old-token' : 'fresh-token');
        });

        const result = await api.getHealth();
        expect(result).toEqual({ status: 'healthy' });
        expect(fetch).toHaveBeenCalledTimes(2);

        const retryHeaders = (fetch as ReturnType<typeof vi.fn>).mock.calls[1][1].headers;
        expect(retryHeaders['Authorization']).toBe('Bearer fresh-token');
    });

    it('throws on 401 when no fresh token available', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            statusText: 'Unauthorized',
            json: () => Promise.resolve({}),
        });

        setTokenSource(() => Promise.resolve('same-token'));

        await expect(api.getHealth()).rejects.toThrow('API request failed');
        await expect(api.getHealth()).rejects.toBeInstanceOf(APIError);
    });
});

describe('AdminAuthBridge', () => {
    afterEach(() => {
        setTokenSource(null);
        vi.restoreAllMocks();
    });

    it('renders children', async () => {
        const { AdminAuthBridge } = await import('@/lib/auth');
        const { container } = render(
            <AdminAuthBridge>
                <div data-testid="child">Hello</div>
            </AdminAuthBridge>
        );
        expect(container.querySelector('[data-testid="child"]')).toBeTruthy();
    });

    it('calls setTokenSource when client is available', async () => {
        const mockGetAccessToken = vi.fn().mockResolvedValue('mock-token');
        const { useJanua } = await import('@janua/nextjs');
        (useJanua as ReturnType<typeof vi.fn>).mockReturnValue({
            client: { getAccessToken: mockGetAccessToken },
            user: { id: '1', email: 'test@test.com' },
            isLoading: false,
            isAuthenticated: true,
            signOut: vi.fn(),
        });

        const { AdminAuthBridge } = await import('@/lib/auth');
        render(
            <AdminAuthBridge>
                <div>Test</div>
            </AdminAuthBridge>
        );

        const mockFetchFn = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ status: 'healthy' }),
        });
        global.fetch = mockFetchFn;

        await api.getHealth();
        const callHeaders = mockFetchFn.mock.calls[0][1].headers;
        expect(callHeaders['Authorization']).toBe('Bearer mock-token');
    });

    it('clears token source on unmount', async () => {
        const mockGetAccessToken = vi.fn().mockResolvedValue('unmount-token');
        const { useJanua } = await import('@janua/nextjs');
        (useJanua as ReturnType<typeof vi.fn>).mockReturnValue({
            client: { getAccessToken: mockGetAccessToken },
            user: { id: '1' },
            isLoading: false,
            isAuthenticated: true,
            signOut: vi.fn(),
        });

        const { AdminAuthBridge } = await import('@/lib/auth');
        const { unmount } = render(
            <AdminAuthBridge>
                <div>Test</div>
            </AdminAuthBridge>
        );

        // Token source should be set
        const mockFetchFn = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ status: 'healthy' }),
        });
        global.fetch = mockFetchFn;
        await api.getHealth();
        expect(mockFetchFn.mock.calls[0][1].headers['Authorization']).toBe('Bearer unmount-token');

        // After unmount, token source should be cleared
        unmount();
        mockFetchFn.mockClear();
        await api.getHealth();
        expect(mockFetchFn.mock.calls[0][1].headers).not.toHaveProperty('Authorization');
    });
});

describe('useAdminAuth', () => {
    it('returns authenticated state when user exists', async () => {
        const mockSignOut = vi.fn();
        const { useJanua } = await import('@janua/nextjs');
        (useJanua as ReturnType<typeof vi.fn>).mockReturnValue({
            client: null,
            user: { id: '42', email: 'admin@madfam.io' },
            isLoading: false,
            isAuthenticated: true,
            signOut: mockSignOut,
        });

        const { useAdminAuth } = await import('@/lib/auth');
        const { result } = renderHook(() => useAdminAuth());

        expect(result.current.isAuthenticated).toBe(true);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.user).toEqual({ id: '42', email: 'admin@madfam.io' });
        expect(result.current.signOut).toBe(mockSignOut);
    });

    it('returns unauthenticated state when no user', async () => {
        const { useJanua } = await import('@janua/nextjs');
        (useJanua as ReturnType<typeof vi.fn>).mockReturnValue({
            client: null,
            user: null,
            isLoading: false,
            isAuthenticated: false,
            signOut: vi.fn(),
        });

        const { useAdminAuth } = await import('@/lib/auth');
        const { result } = renderHook(() => useAdminAuth());

        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.user).toBeNull();
    });

    it('returns loading state during auth check', async () => {
        const { useJanua } = await import('@janua/nextjs');
        (useJanua as ReturnType<typeof vi.fn>).mockReturnValue({
            client: null,
            user: null,
            isLoading: true,
            isAuthenticated: false,
            signOut: vi.fn(),
        });

        const { useAdminAuth } = await import('@/lib/auth');
        const { result } = renderHook(() => useAdminAuth());

        expect(result.current.isLoading).toBe(true);
        expect(result.current.isAuthenticated).toBe(false);
    });
});
