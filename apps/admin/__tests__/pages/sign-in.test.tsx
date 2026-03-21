import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const mockReplace = vi.fn();
const mockGet = vi.fn(() => null);
const mockUseAuth = vi.fn(() => ({
    isAuthenticated: false,
    isLoading: false,
}));

vi.mock('@/lib/auth', () => ({
    useAuth: () => mockUseAuth(),
}));

vi.mock('@janua/ui/components/auth', () => ({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SignIn: (props: any) => (
        <div data-testid="janua-sign-in" data-api-url={props.apiUrl} />
    ),
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
    useSearchParams: () => ({ get: mockGet }),
}));

vi.mock('lucide-react', () => ({
    Lock: () => <svg data-testid="lock-icon" />,
    Shield: () => <svg data-testid="shield-icon" />,
}));

describe('SignInPage', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        mockReplace.mockReset();
        mockGet.mockReturnValue(null);
        mockUseAuth.mockReturnValue({
            isAuthenticated: false,
            isLoading: false,
        });
    });

    afterEach(() => {
        process.env = originalEnv;
        vi.resetModules();
    });

    it('renders SSO button, divider, and Janua SignIn component', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByText('Iniciar sesión con Janua SSO')).toBeInTheDocument();
        expect(screen.getByText(/proveedor de identidad/)).toBeInTheDocument();
        expect(screen.getByText('o usa correo y contraseña')).toBeInTheDocument();
        expect(screen.getByTestId('janua-sign-in')).toBeInTheDocument();
    });

    it('navigates to /api/auth/sso on SSO button click', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };

        const originalLocation = window.location;
        // @ts-expect-error — override for test
        delete window.location;
        window.location = { ...originalLocation, origin: 'http://localhost:3000', href: '' } as Location;

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        fireEvent.click(screen.getByText('Iniciar sesión con Janua SSO'));

        expect(window.location.href).toBe('/api/auth/sso');

        window.location = originalLocation;
    });

    it('shows SSO error from query parameter', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockGet.mockImplementation((key: string) =>
            key === 'sso_error' ? 'Token exchange failed' : null
        );

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent('Token exchange failed');
        });
    });

    it('shows loading spinner while auth is loading', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockUseAuth.mockReturnValue({
            isAuthenticated: false,
            isLoading: true,
        });

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByText('Cargando...')).toBeInTheDocument();
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

    it('redirects to / when already authenticated', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockUseAuth.mockReturnValue({
            isAuthenticated: true,
            isLoading: false,
        });

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        await waitFor(() => {
            expect(mockReplace).toHaveBeenCalledWith('/');
        });
    });
});
