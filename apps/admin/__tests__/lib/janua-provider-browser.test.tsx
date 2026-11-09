import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const baseProvider = vi.hoisted(() =>
    vi.fn(({ children }: { children: React.ReactNode; config: unknown }) => <>{children}</>),
);
vi.mock('@janua/nextjs', () => ({
    JanuaProvider: baseProvider,
    UserButton: () => null,
    SignInForm: () => null,
    useJanua: vi.fn(() => ({ client: null })),
    useAuth: vi.fn(),
}));

import { JanuaProvider } from '@/lib/auth';

const LAYOUT_CONFIG = {
    baseURL: 'https://auth.example.test',
    apiKey: 'pk_test_synthetic',
    autoRefreshTokens: true,
    skipRemoteAuth: true,
};

// jsdom has `window`: the browser keeps the layout config, auto-refresh on.
describe('admin JanuaProvider in the browser', () => {
    afterEach(() => {
        baseProvider.mockClear();
    });

    it('passes the layout config through unchanged (same object, refresh on)', () => {
        const { getByText } = render(
            <JanuaProvider config={LAYOUT_CONFIG}>
                <p>child</p>
            </JanuaProvider>,
        );
        expect(getByText('child')).toBeInTheDocument();
        const passed = baseProvider.mock.calls[0][0].config;
        expect(passed).toBe(LAYOUT_CONFIG);
        expect(LAYOUT_CONFIG.autoRefreshTokens).toBe(true);
    });
});
