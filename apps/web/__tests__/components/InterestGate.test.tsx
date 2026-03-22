import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../helpers/auth-mock';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => (
        <a href={href} {...props}>{children}</a>
    ),
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

// Mock config
vi.mock('@/lib/config', () => ({
    API_BASE_URL: 'http://localhost:8000/api/v1',
}));

// Mock feature-labels
vi.mock('@/lib/feature-labels', () => ({
    getFeatureLabel: (key: string, lang: string) => {
        const labels: Record<string, Record<string, string>> = {
            latex_export: { es: 'Exportar LaTeX', en: 'LaTeX export', nah: 'LaTeX tēmōhuiliztli' },
            advanced_search: { es: 'Búsqueda avanzada', en: 'Advanced search', nah: 'Huēyi tlatemoliztli' },
        };
        return labels[key]?.[lang] ?? key;
    },
}));

// Mock PostHog
const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => (
        <div data-testid="card" className={className}>{children}</div>
    ),
    CardContent: ({ children, className }: any) => (
        <div className={className}>{children}</div>
    ),
    Badge: ({ children, className }: any) => (
        <span data-testid="badge" className={className}>{children}</span>
    ),
    Button: ({ children, className, ...props }: any) => (
        <button className={className} {...props}>{children}</button>
    ),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Bell: ({ className }: any) => <span data-testid="bell-icon" className={className} />,
    X: ({ className }: any) => <span data-testid="x-icon" className={className} />,
    Check: ({ className }: any) => <span data-testid="check-icon" className={className} />,
    Loader2: ({ className }: any) => <span data-testid="loader-icon" className={className} />,
}));

import { InterestGate } from '@/components/InterestGate';

describe('InterestGate', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es' as const, setLang: vi.fn() });
        mockUseAuth.mockReturnValue(defaultAuthState);
        global.fetch = vi.fn();
    });

    describe('inline variant', () => {
        it('renders coming soon badge and feature label', () => {
            render(<InterestGate variant="inline" featureKey="latex_export" />);
            expect(screen.getByText('Disponible pronto')).toBeDefined();
            expect(screen.getByText('Exportar LaTeX')).toBeDefined();
        });

        it('renders email input and submit button', () => {
            render(<InterestGate variant="inline" featureKey="latex_export" />);
            expect(screen.getByPlaceholderText('tu@correo.com')).toBeDefined();
            expect(screen.getByText('Notificarme')).toBeDefined();
        });
    });

    describe('card variant', () => {
        it('renders with benefits list', () => {
            render(
                <InterestGate
                    variant="card"
                    featureKey="latex_export"
                    benefits={['100 resultados', 'LaTeX export']}
                />
            );
            expect(screen.getByText('100 resultados')).toBeDefined();
            expect(screen.getByText('LaTeX export')).toBeDefined();
        });

        it('renders use case dropdown when showUseCase is true', () => {
            render(
                <InterestGate
                    variant="card"
                    featureKey="latex_export"
                    showUseCase
                />
            );
            expect(screen.getByText('¿Para qué lo usarías?')).toBeDefined();
            expect(screen.getByText('Investigación')).toBeDefined();
            expect(screen.getByText('Trabajo')).toBeDefined();
        });
    });

    describe('toast variant', () => {
        it('renders with dismiss button', () => {
            render(<InterestGate variant="toast" featureKey="latex_export" />);
            expect(screen.getByLabelText('Cerrar')).toBeDefined();
        });

        it('dismisses on click', () => {
            const onDismiss = vi.fn();
            render(<InterestGate variant="toast" featureKey="latex_export" onDismiss={onDismiss} />);
            fireEvent.click(screen.getByLabelText('Cerrar'));
            expect(onDismiss).toHaveBeenCalled();
        });
    });

    describe('overlay variant', () => {
        it('renders with backdrop', () => {
            const { container } = render(
                <InterestGate variant="overlay" featureKey="latex_export" />
            );
            expect(container.querySelector('.backdrop-blur-sm')).not.toBeNull();
        });
    });

    describe('form submission', () => {
        it('posts to interest endpoint on submit', async () => {
            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
                status: 201,
                json: () => Promise.resolve({ status: 'registered' }),
            });

            render(<InterestGate variant="inline" featureKey="latex_export" sourcePage="export_dropdown" />);

            const emailInput = screen.getByPlaceholderText('tu@correo.com');
            fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
            fireEvent.submit(emailInput.closest('form')!);

            await waitFor(() => {
                expect(global.fetch).toHaveBeenCalledWith(
                    'http://localhost:8000/api/v1/interest/',
                    expect.objectContaining({
                        method: 'POST',
                        body: expect.stringContaining('latex_export'),
                    }),
                );
            });
        });

        it('shows success message after registration', async () => {
            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
                status: 201,
            });

            render(<InterestGate variant="inline" featureKey="latex_export" />);

            fireEvent.change(screen.getByPlaceholderText('tu@correo.com'), {
                target: { value: 'test@example.com' },
            });
            fireEvent.submit(screen.getByPlaceholderText('tu@correo.com').closest('form')!);

            await waitFor(() => {
                expect(screen.getByText('¡Listo! Te avisaremos.')).toBeDefined();
            });
        });

        it('shows already registered message on duplicate', async () => {
            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
                status: 200,
            });

            render(<InterestGate variant="inline" featureKey="latex_export" />);

            fireEvent.change(screen.getByPlaceholderText('tu@correo.com'), {
                target: { value: 'test@example.com' },
            });
            fireEvent.submit(screen.getByPlaceholderText('tu@correo.com').closest('form')!);

            await waitFor(() => {
                expect(screen.getByText('Ya te notificaremos.')).toBeDefined();
            });
        });

        it('shows error message on failure', async () => {
            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
                status: 500,
            });

            render(<InterestGate variant="inline" featureKey="latex_export" />);

            fireEvent.change(screen.getByPlaceholderText('tu@correo.com'), {
                target: { value: 'test@example.com' },
            });
            fireEvent.submit(screen.getByPlaceholderText('tu@correo.com').closest('form')!);

            await waitFor(() => {
                expect(screen.getByText('Error al registrar. Intenta de nuevo.')).toBeDefined();
            });
        });
    });

    describe('PostHog tracking', () => {
        it('tracks shown event on mount', () => {
            render(<InterestGate variant="inline" featureKey="latex_export" />);
            expect(mockTrackEvent).toHaveBeenCalledWith('interest_gate.shown', {
                variant: 'inline',
                feature_key: 'latex_export',
            });
        });

        it('tracks dismissed event', () => {
            render(<InterestGate variant="toast" featureKey="latex_export" />);
            fireEvent.click(screen.getByLabelText('Cerrar'));
            expect(mockTrackEvent).toHaveBeenCalledWith('interest_gate.dismissed', {
                variant: 'toast',
                feature_key: 'latex_export',
            });
        });
    });

    describe('i18n', () => {
        it('renders English content', () => {
            mockUseLang.mockReturnValue({ lang: 'en' as const, setLang: vi.fn() });
            render(<InterestGate variant="inline" featureKey="latex_export" />);
            expect(screen.getByText('Coming soon')).toBeDefined();
            expect(screen.getByText('Notify me')).toBeDefined();
            expect(screen.getByText('LaTeX export')).toBeDefined();
        });

        it('renders Nahuatl content', () => {
            mockUseLang.mockReturnValue({ lang: 'nah' as const, setLang: vi.fn() });
            render(<InterestGate variant="inline" featureKey="latex_export" />);
            expect(screen.getByText('Hualaz niman')).toBeDefined();
            expect(screen.getByText('Xinechtlanonotza')).toBeDefined();
        });
    });

    describe('custom feature label', () => {
        it('uses featureLabel prop over default', () => {
            render(
                <InterestGate
                    variant="inline"
                    featureKey="latex_export"
                    featureLabel="Custom LaTeX Label"
                />
            );
            expect(screen.getByText('Custom LaTeX Label')).toBeDefined();
        });
    });

    describe('pre-filled email from auth', () => {
        it('pre-fills email for authenticated users', () => {
            mockUseAuth.mockReturnValue(mockAuth({
                isAuthenticated: true,
                email: 'auth@example.com',
                tier: 'community',
            }));
            render(<InterestGate variant="inline" featureKey="latex_export" />);
            const input = screen.getByPlaceholderText('tu@correo.com') as HTMLInputElement;
            expect(input.value).toBe('auth@example.com');
        });
    });
});
