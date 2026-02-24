import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const mockSignIn = vi.fn();
const mockGetOAuthProviders = vi.fn();
const mockSignInWithOAuth = vi.fn();
const mockReplace = vi.fn();
const mockUseAuth = vi.fn(() => ({
    auth: {
        signIn: mockSignIn,
        getOAuthProviders: mockGetOAuthProviders,
        signInWithOAuth: mockSignInWithOAuth,
    },
    user: null,
    session: null,
    isAuthenticated: false,
    isLoading: false,
    signOut: vi.fn(),
}));

vi.mock('@janua/nextjs', () => ({
    JanuaProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    UserButton: () => <div data-testid="user-button" />,
    SignInForm: ({ redirectTo }: { redirectTo: string }) => (
        <div data-testid="sign-in-form" data-redirect={redirectTo} />
    ),
    useJanua: vi.fn(() => ({
        client: null,
        user: null,
        isLoading: false,
        isAuthenticated: false,
        signOut: vi.fn(),
    })),
    useAuth: () => mockUseAuth(),
}));

vi.mock('next/link', () => ({
    default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({ replace: mockReplace }),
}));

vi.mock('lucide-react', () => ({
    Lock: () => <svg data-testid="lock-icon" />,
    Shield: () => <svg data-testid="shield-icon" />,
}));

describe('SignInPage', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        mockSignIn.mockReset();
        mockGetOAuthProviders.mockReset();
        mockSignInWithOAuth.mockReset();
        mockReplace.mockReset();
        mockUseAuth.mockReturnValue({
            auth: {
                signIn: mockSignIn,
                getOAuthProviders: mockGetOAuthProviders,
                signInWithOAuth: mockSignInWithOAuth,
            },
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            signOut: vi.fn(),
        });
        // Default: no providers
        mockGetOAuthProviders.mockResolvedValue([]);
    });

    afterEach(() => {
        process.env = originalEnv;
        vi.resetModules();
    });

    it('renders SSO button when OAuth providers are available', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([
            { provider: 'janua', name: 'Janua SSO', enabled: true },
        ]);

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByText('Iniciar sesión con Janua SSO')).toBeInTheDocument();
        });
        expect(screen.getByText(/proveedor de identidad/)).toBeInTheDocument();
    });

    it('calls initiateOAuth and redirects on SSO button click', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([
            { provider: 'janua', name: 'Janua SSO', enabled: true },
        ]);
        mockSignInWithOAuth.mockResolvedValue({
            authorization_url: 'https://auth.example.com/authorize?state=abc',
            state: 'abc',
            provider: 'janua',
        });

        const originalLocation = window.location;
        // @ts-expect-error — override for test
        delete window.location;
        window.location = { ...originalLocation, origin: 'http://localhost:3000', href: '' } as Location;

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByText('Iniciar sesión con Janua SSO')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Iniciar sesión con Janua SSO'));

        await waitFor(() => {
            expect(mockSignInWithOAuth).toHaveBeenCalledWith({
                provider: 'janua',
                redirect_uri: 'http://localhost:3000/sign-in',
            });
            expect(window.location.href).toBe('https://auth.example.com/authorize?state=abc');
        });

        window.location = originalLocation;
    });

    it('shows SSO error when initiateOAuth fails', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([
            { provider: 'janua', name: 'Janua SSO', enabled: true },
        ]);
        mockSignInWithOAuth.mockRejectedValue(new Error('OAuth unavailable'));

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByText('Iniciar sesión con Janua SSO')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Iniciar sesión con Janua SSO'));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('OAuth unavailable');
        });
    });

    it('shows email/password fallback when no OAuth providers are available', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([]);

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument();
        });
        expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeInTheDocument();
    });

    it('shows email/password fallback when getOAuthProviders fails', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockRejectedValue(new Error('Network error'));

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument();
        });
        expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
    });

    it('shows loading spinner while fetching providers', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        // Never resolve to keep loading state
        mockGetOAuthProviders.mockImplementation(() => new Promise(() => {}));

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByText('Cargando...')).toBeInTheDocument();
    });

    it('shows error message on failed email/password sign-in', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([]);
        mockSignIn.mockRejectedValueOnce(new Error('Credenciales inválidas'));

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByLabelText('Correo electrónico'), {
            target: { value: 'test@example.com' },
        });
        fireEvent.change(screen.getByLabelText('Contraseña'), {
            target: { value: 'wrong' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('Credenciales inválidas');
        });
    });

    it('shows loading state during email/password submission', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([]);
        mockSignIn.mockImplementation(() => new Promise(() => {})); // never resolves

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByLabelText('Correo electrónico'), {
            target: { value: 'test@example.com' },
        });
        fireEvent.change(screen.getByLabelText('Contraseña'), {
            target: { value: 'pass' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));

        await waitFor(() => {
            expect(screen.getByRole('button', { name: 'Iniciando sesión...' })).toBeDisabled();
        });
    });

    it('renders fallback message when Janua is not configured', async () => {
        process.env = { ...originalEnv };
        delete process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByText('Autenticación no configurada')).toBeInTheDocument();
        expect(screen.getByText(/variables de entorno de Janua/)).toBeInTheDocument();
    });

    it('shows dev bypass link when unconfigured', async () => {
        process.env = { ...originalEnv };
        delete process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        const link = screen.getByText('Continuar sin autenticación');
        expect(link).toBeInTheDocument();
        expect(link.closest('a')).toHaveAttribute('href', '/');
    });

    it('shows env var instructions in code block', async () => {
        process.env = { ...originalEnv };
        delete process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByText(/NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY/)).toBeInTheDocument();
        expect(screen.getByText(/JANUA_SECRET_KEY/)).toBeInTheDocument();
    });

    it('renders multiple SSO buttons for multiple providers', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([
            { provider: 'janua', name: 'Janua SSO', enabled: true },
            { provider: 'google', name: 'Google', enabled: true },
        ]);

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByText('Iniciar sesión con Janua SSO')).toBeInTheDocument();
            expect(screen.getByText('Iniciar sesión con Google')).toBeInTheDocument();
        });
    });

    it('filters out disabled providers', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([
            { provider: 'janua', name: 'Janua SSO', enabled: true },
            { provider: 'github', name: 'GitHub', enabled: false },
        ]);

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByText('Iniciar sesión con Janua SSO')).toBeInTheDocument();
        });
        expect(screen.queryByText('Iniciar sesión con GitHub')).not.toBeInTheDocument();
    });

    it('redirects to / when already authenticated', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGetOAuthProviders.mockResolvedValue([]);
        mockUseAuth.mockReturnValue({
            auth: {
                signIn: mockSignIn,
                getOAuthProviders: mockGetOAuthProviders,
                signInWithOAuth: mockSignInWithOAuth,
            },
            user: { id: '1', email: 'test@example.com' },
            session: {},
            isAuthenticated: true,
            isLoading: false,
            signOut: vi.fn(),
        });

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(mockReplace).toHaveBeenCalledWith('/');
        });
    });
});
