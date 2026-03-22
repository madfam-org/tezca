import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../helpers/auth-mock';

// Mock next/navigation
const mockReplace = vi.fn();
const mockSearchParams = new URLSearchParams();
vi.mock('next/navigation', () => ({
    useRouter: () => ({ replace: mockReplace }),
    useSearchParams: () => mockSearchParams,
}));

// Mock @janua/nextjs
vi.mock('@janua/nextjs', () => ({
    useJanua: () => ({ client: {} }),
}));

// Mock @janua/ui
vi.mock('@janua/ui', () => ({
    SignIn: (props: any) => <div data-testid="sign-in" />,
    SignUp: (props: any) => <div data-testid="sign-up" />,
}));

// Mock LanguageContext
const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

// Mock AuthContext
const mockUseAuth = vi.fn(() => defaultAuthState);
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

// Mock PostHog
const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

import LoginPage from '@/app/login/page';

describe('LoginPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(defaultAuthState);
    });

    it('renders sign-in form by default', () => {
        render(<LoginPage />);
        expect(screen.getByText('Iniciar sesi\u00f3n')).toBeDefined();
        expect(screen.getByTestId('sign-in')).toBeDefined();
    });

    it('toggles to sign-up mode', () => {
        render(<LoginPage />);
        fireEvent.click(screen.getByText('\u00bfNo tienes cuenta? Reg\u00edstrate'));
        expect(screen.getByText('Crear cuenta')).toBeDefined();
        expect(screen.getByTestId('sign-up')).toBeDefined();
    });

    it('redirects when already authenticated', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true }));
        render(<LoginPage />);
        expect(mockReplace).toHaveBeenCalledWith('/cuenta');
    });

    it('renders English content', () => {
        mockUseLang.mockReturnValue({ lang: 'en' as const, setLang: vi.fn() });
        render(<LoginPage />);
        expect(screen.getByText('Sign in')).toBeDefined();
    });

    it('renders Nahuatl content', () => {
        mockUseLang.mockReturnValue({ lang: 'nah' as const, setLang: vi.fn() });
        render(<LoginPage />);
        expect(screen.getByText('Xicalaqui')).toBeDefined();
    });

    it('tracks login page viewed event', () => {
        render(<LoginPage />);
        expect(mockTrackEvent).toHaveBeenCalledWith('auth.login_page_viewed', { mode: 'signin' });
    });

    it('tracks auth.mode_switched when toggling to signup', () => {
        render(<LoginPage />);
        fireEvent.click(screen.getByText('\u00bfNo tienes cuenta? Reg\u00edstrate'));
        expect(mockTrackEvent).toHaveBeenCalledWith('auth.mode_switched', {
            from: 'signin',
            to: 'signup',
        });
    });
});
