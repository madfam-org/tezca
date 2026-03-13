import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock @janua/nextjs — control auth state per test
const mockJanuaAuth = vi.fn(() => ({
    isAuthenticated: false,
    user: null,
    isLoading: false,
}));
const mockSignOut = vi.fn();
const mockJanuaClient = { signOut: mockSignOut };

vi.mock('@janua/nextjs', () => ({
    useAuth: () => mockJanuaAuth(),
    useJanua: () => ({ client: mockJanuaClient }),
    JanuaProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    SignedIn: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    SignedOut: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { AuthProvider, useAuth } from '@/components/providers/AuthContext';

/** Helper component that displays auth state for test assertions. */
function AuthDisplay() {
    const auth = useAuth();
    return (
        <div>
            <span data-testid="authenticated">{String(auth.isAuthenticated)}</span>
            <span data-testid="tier">{auth.tier}</span>
            <span data-testid="userId">{auth.userId ?? 'null'}</span>
            <span data-testid="email">{auth.email ?? 'null'}</span>
            <span data-testid="name">{auth.name ?? 'null'}</span>
            <button data-testid="sign-out" onClick={auth.signOut}>
                Sign out
            </button>
        </div>
    );
}

/** Create a base64-encoded JWT payload (header.payload.signature). */
function makeJwt(payload: Record<string, unknown>): string {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const body = btoa(JSON.stringify(payload));
    return `${header}.${body}.fakesig`;
}

describe('AuthContext', () => {
    const originalLocation = window.location;

    beforeEach(() => {
        vi.clearAllMocks();
        document.cookie = 'janua_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        localStorage.removeItem('janua_token');
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: false,
            user: null,
            isLoading: false,
        });
    });

    afterEach(() => {
        Object.defineProperty(window, 'location', {
            writable: true,
            value: originalLocation,
        });
    });

    // ---------------------------------------------------------------
    // 1. Default unauthenticated state
    // ---------------------------------------------------------------
    it('provides default unauthenticated state', () => {
        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('authenticated').textContent).toBe('false');
        expect(screen.getByTestId('tier').textContent).toBe('anon');
        expect(screen.getByTestId('userId').textContent).toBe('null');
    });

    // ---------------------------------------------------------------
    // 2. Provider renders children
    // ---------------------------------------------------------------
    it('renders children correctly', () => {
        render(
            <AuthProvider>
                <span data-testid="child">Hello</span>
            </AuthProvider>,
        );

        expect(screen.getByTestId('child').textContent).toBe('Hello');
    });

    // ---------------------------------------------------------------
    // 3. Authenticated via Janua
    // ---------------------------------------------------------------
    it('reads authenticated state from Janua SDK', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: {
                sub: 'user-123',
                email: 'user@tezca.mx',
                name: 'Test User',
                tier: 'pro',
            },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('authenticated').textContent).toBe('true');
        expect(screen.getByTestId('tier').textContent).toBe('pro');
        expect(screen.getByTestId('userId').textContent).toBe('user-123');
        expect(screen.getByTestId('email').textContent).toBe('user@tezca.mx');
        expect(screen.getByTestId('name').textContent).toBe('Test User');
    });

    // ---------------------------------------------------------------
    // 4. Tier normalization: 'free' -> 'essentials'
    // ---------------------------------------------------------------
    it('normalizes "free" tier to "essentials"', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u1', tier: 'free' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('tier').textContent).toBe('essentials');
    });

    // ---------------------------------------------------------------
    // 5. Tier normalization: 'premium' -> 'pro'
    // ---------------------------------------------------------------
    it('normalizes "premium" tier to "pro"', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u2', tier: 'premium' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('tier').textContent).toBe('pro');
    });

    // ---------------------------------------------------------------
    // 6. Tier normalization: 'enterprise' -> 'pro'
    // ---------------------------------------------------------------
    it('normalizes "enterprise" tier to "pro"', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u3', tier: 'enterprise' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('tier').textContent).toBe('pro');
    });

    // ---------------------------------------------------------------
    // 7. Tier normalization: 'internal' -> 'madfam'
    // ---------------------------------------------------------------
    it('normalizes "internal" tier to "madfam"', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u4', tier: 'internal' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('tier').textContent).toBe('madfam');
    });

    // ---------------------------------------------------------------
    // 8. Unknown tier defaults to 'essentials'
    // ---------------------------------------------------------------
    it('defaults unknown tier to "essentials"', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u5', tier: 'garbage_value' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('tier').textContent).toBe('essentials');
    });

    // ---------------------------------------------------------------
    // 9. Fallback to JWT cookie when Janua is not authenticated
    // ---------------------------------------------------------------
    it('reads auth state from JWT cookie as fallback', () => {
        const token = makeJwt({
            sub: 'cookie-user',
            email: 'cookie@tezca.mx',
            name: 'Cookie User',
            tier: 'community',
        });
        document.cookie = `janua_token=${encodeURIComponent(token)}`;

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('authenticated').textContent).toBe('true');
        expect(screen.getByTestId('tier').textContent).toBe('community');
        expect(screen.getByTestId('userId').textContent).toBe('cookie-user');
    });

    // ---------------------------------------------------------------
    // 10. Fallback to localStorage JWT token
    // ---------------------------------------------------------------
    it('reads auth state from localStorage JWT as fallback', () => {
        const token = makeJwt({
            sub: 'ls-user',
            email: 'ls@tezca.mx',
            tier: 'pro',
        });
        localStorage.setItem('janua_token', token);

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('authenticated').textContent).toBe('true');
        expect(screen.getByTestId('tier').textContent).toBe('pro');
    });

    // ---------------------------------------------------------------
    // 11. Invalid JWT returns unauthenticated
    // ---------------------------------------------------------------
    it('returns unauthenticated for invalid JWT', () => {
        document.cookie = 'janua_token=not-a-jwt';

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('authenticated').textContent).toBe('false');
        expect(screen.getByTestId('tier').textContent).toBe('anon');
    });

    // ---------------------------------------------------------------
    // 12. User ID from user_id claim (fallback)
    // ---------------------------------------------------------------
    it('reads user_id claim when sub is not present', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { user_id: 'alt-id', tier: 'essentials' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('userId').textContent).toBe('alt-id');
    });

    // ---------------------------------------------------------------
    // 13. Name from full_name claim (fallback)
    // ---------------------------------------------------------------
    it('reads full_name claim when name is not present', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u6', full_name: 'Full Name User', tier: 'pro' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('name').textContent).toBe('Full Name User');
    });

    // ---------------------------------------------------------------
    // 14. useAuth outside provider returns default state
    // ---------------------------------------------------------------
    it('useAuth outside provider returns default unauthenticated state', () => {
        // Render without AuthProvider — useContext returns default
        render(<AuthDisplay />);

        expect(screen.getByTestId('authenticated').textContent).toBe('false');
        expect(screen.getByTestId('tier').textContent).toBe('anon');
    });

    // ---------------------------------------------------------------
    // 15. Reads plan claim when tier is absent
    // ---------------------------------------------------------------
    it('reads plan claim when tier is not present', () => {
        mockJanuaAuth.mockReturnValue({
            isAuthenticated: true,
            user: { sub: 'u7', plan: 'community' },
            isLoading: false,
        });

        render(
            <AuthProvider>
                <AuthDisplay />
            </AuthProvider>,
        );

        expect(screen.getByTestId('tier').textContent).toBe('community');
    });
});
