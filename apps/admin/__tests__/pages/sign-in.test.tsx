import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const mockSignIn = vi.fn();
const mockReplace = vi.fn();
const mockUseAuth = vi.fn(() => ({
    auth: { signIn: mockSignIn },
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

describe('SignInPage', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        mockSignIn.mockReset();
        mockReplace.mockReset();
        mockUseAuth.mockReturnValue({
            auth: { signIn: mockSignIn },
            user: null,
            session: null,
            isAuthenticated: false,
            isLoading: false,
            signOut: vi.fn(),
        });
    });

    afterEach(() => {
        process.env = originalEnv;
        vi.resetModules();
    });

    it('renders email and password inputs when Janua is configured', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument();
        expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
        expect(screen.getByText('Tezca Admin')).toBeInTheDocument();
    });

    it('renders submit button with correct text', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeInTheDocument();
    });

    it('shows error message on failed sign-in', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockSignIn.mockRejectedValueOnce(new Error('Credenciales inválidas'));

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

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

    it('shows loading state during submission', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };
        mockSignIn.mockImplementation(() => new Promise(() => {})); // never resolves

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

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
});
