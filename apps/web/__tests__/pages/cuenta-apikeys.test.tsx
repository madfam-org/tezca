import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../helpers/auth-mock';

// Mock next/navigation
vi.mock('next/navigation', () => ({
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => '/cuenta/apikeys',
}));

// Mock @janua/nextjs
vi.mock('@janua/nextjs', () => ({
    useJanua: () => ({ client: {} }),
    Protect: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div data-testid="card" className={className}>{children}</div>
    ),
    Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

// Mock LanguageContext
const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

// Mock AuthContext
const mockUseAuth = vi.fn(() => mockAuth({ isAuthenticated: true, tier: 'academic' }));
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

// Mock auth token
vi.mock('@/lib/auth-token', () => ({
    getAuthToken: () => 'fake-token',
}));

// Mock PostHog
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: vi.fn(),
}));

// Mock InterestGate
vi.mock('@/components/InterestGate', () => ({
    InterestGate: ({ featureKey }: { featureKey: string }) => (
        <div data-testid="interest-gate">{featureKey}</div>
    ),
}));

// Mock API
const mockGetUserApiKeys = vi.fn();
const mockCreateUserApiKey = vi.fn();
const mockRevokeUserApiKey = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        getUserApiKeys: (...args: any[]) => mockGetUserApiKeys(...args),
        createUserApiKey: (...args: any[]) => mockCreateUserApiKey(...args),
        revokeUserApiKey: (...args: any[]) => mockRevokeUserApiKey(...args),
    },
}));

import ApiKeysPage from '@/app/cuenta/apikeys/page';

describe('ApiKeysPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'academic' }));
        mockGetUserApiKeys.mockResolvedValue({ keys: [], total: 0 });
    });

    it('renders title and empty state', async () => {
        render(<ApiKeysPage />);
        expect(screen.getByText('Llaves de API')).toBeDefined();
        await waitFor(() => {
            expect(screen.getByText('No tienes llaves de API. Crea una para comenzar.')).toBeDefined();
        });
    });

    it('shows loading state initially', () => {
        mockGetUserApiKeys.mockReturnValue(new Promise(() => {})); // never resolves
        render(<ApiKeysPage />);
        expect(screen.getByText('Cargando llaves...')).toBeDefined();
    });

    it('renders key list with prefix, name, and tier badge', async () => {
        mockGetUserApiKeys.mockResolvedValue({
            keys: [
                {
                    prefix: 'abcd1234',
                    name: 'Test Key',
                    tier: 'academic',
                    scopes: ['read', 'search', 'export'],
                    is_active: true,
                    created_at: '2026-01-15T00:00:00Z',
                    last_used_at: null,
                },
            ],
            total: 1,
        });
        render(<ApiKeysPage />);
        await waitFor(() => {
            expect(screen.getByText('Test Key')).toBeDefined();
            expect(screen.getByText('tzk_abcd1234...')).toBeDefined();
            expect(screen.getByText('Activa')).toBeDefined();
        });
    });

    it('create button opens form and submit shows secret', async () => {
        mockCreateUserApiKey.mockResolvedValue({
            prefix: 'newkey01',
            name: 'New Key',
            tier: 'academic',
            scopes: ['read', 'search'],
            is_active: true,
            created_at: '2026-03-22T00:00:00Z',
            last_used_at: null,
            key: 'tzk_full-secret-key-value-12345678',
        });

        render(<ApiKeysPage />);
        await waitFor(() => {
            expect(screen.getByText(/Crear llave/)).toBeDefined();
        });

        // Click create button
        fireEvent.click(screen.getByText(/Crear llave/));
        expect(screen.getByPlaceholderText('e.g. Mi aplicación')).toBeDefined();

        // Fill name and submit
        fireEvent.change(screen.getByPlaceholderText('e.g. Mi aplicación'), {
            target: { value: 'New Key' },
        });
        fireEvent.click(screen.getByText('Crear'));

        await waitFor(() => {
            expect(screen.getByText('tzk_full-secret-key-value-12345678')).toBeDefined();
            expect(screen.getByText(/Guarda esta llave/)).toBeDefined();
        });
    });

    it('copy button triggers clipboard write', async () => {
        const mockWriteText = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, { clipboard: { writeText: mockWriteText } });

        mockCreateUserApiKey.mockResolvedValue({
            prefix: 'cpykey01',
            name: 'Copy Key',
            tier: 'academic',
            scopes: ['read'],
            is_active: true,
            created_at: '2026-03-22T00:00:00Z',
            last_used_at: null,
            key: 'tzk_copy-me-secret-key',
        });

        render(<ApiKeysPage />);
        await waitFor(() => expect(screen.getByText(/Crear llave/)).toBeDefined());
        fireEvent.click(screen.getByText(/Crear llave/));
        fireEvent.change(screen.getByPlaceholderText('e.g. Mi aplicación'), {
            target: { value: 'Copy Key' },
        });
        fireEvent.click(screen.getByText('Crear'));

        await waitFor(() => {
            expect(screen.getByText('tzk_copy-me-secret-key')).toBeDefined();
        });

        fireEvent.click(screen.getByText('Copiar'));
        await waitFor(() => {
            expect(mockWriteText).toHaveBeenCalledWith('tzk_copy-me-secret-key');
        });
    });

    it('revoke marks key as inactive', async () => {
        mockGetUserApiKeys.mockResolvedValue({
            keys: [
                {
                    prefix: 'revk1234',
                    name: 'Revoke Me',
                    tier: 'academic',
                    scopes: ['read', 'search'],
                    is_active: true,
                    created_at: '2026-01-15T00:00:00Z',
                    last_used_at: null,
                },
            ],
            total: 1,
        });
        mockRevokeUserApiKey.mockResolvedValue(undefined);

        render(<ApiKeysPage />);
        await waitFor(() => expect(screen.getByText('Revoke Me')).toBeDefined());

        fireEvent.click(screen.getByRole('button', { name: 'Revocar' }));
        await waitFor(() => {
            expect(mockRevokeUserApiKey).toHaveBeenCalledWith('fake-token', 'revk1234');
            expect(screen.getByText('Revocada')).toBeDefined();
        });
    });

    it('shows InterestGate for anon tier', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: false, tier: 'anon' }));
        render(<ApiKeysPage />);
        expect(screen.getByTestId('interest-gate')).toBeDefined();
    });

    it('renders English content', async () => {
        mockUseLang.mockReturnValue({ lang: 'en' as const, setLang: vi.fn() });
        render(<ApiKeysPage />);
        expect(screen.getByText('API Keys')).toBeDefined();
        await waitFor(() => {
            expect(screen.getByText('No API keys yet. Create one to get started.')).toBeDefined();
        });
    });
});
