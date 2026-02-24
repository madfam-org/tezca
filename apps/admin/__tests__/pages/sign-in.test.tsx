import { render, screen } from '@testing-library/react';

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
}));

vi.mock('next/link', () => ({
    default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

describe('SignInPage', () => {
    const originalEnv = process.env;

    afterEach(() => {
        process.env = originalEnv;
        vi.resetModules();
    });

    it('renders sign-in form when Janua is configured', async () => {
        process.env = { ...originalEnv, NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY: 'jnc_test_key' };

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByTestId('sign-in-form')).toBeInTheDocument();
        expect(screen.getByTestId('sign-in-form')).toHaveAttribute('data-redirect', '/');
        expect(screen.getByText('Tezca Admin')).toBeInTheDocument();
    });

    it('renders fallback message when Janua is not configured', async () => {
        process.env = { ...originalEnv };
        delete process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

        const { default: SignInPage } = await import('@/app/sign-in/page');
        render(<SignInPage />);

        expect(screen.getByText('Autenticación no configurada')).toBeInTheDocument();
        expect(screen.getByText(/variables de entorno de Janua/)).toBeInTheDocument();
        expect(screen.queryByTestId('sign-in-form')).not.toBeInTheDocument();
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
