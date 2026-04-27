import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mockAuth } from '../helpers/auth-mock';

// Mock next/navigation
vi.mock('next/navigation', () => ({
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(),
    usePathname: () => '/cuenta/billing',
}));

// Mock @janua/nextjs (Protect should be a passthrough in tests)
vi.mock('@janua/nextjs', () => ({
    useJanua: () => ({ client: {} }),
    Protect: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: () => ({ lang: 'es' as const, setLang: vi.fn() }),
}));

// Mock AuthContext (overridable per test)
const mockUseAuth = vi.fn();
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: () => mockUseAuth(),
}));

// Mock the MONETIZATION_ENABLED flag (overridable per test)
const mockMonetization = vi.fn(() => false);
vi.mock('@/lib/config', () => ({
    get MONETIZATION_ENABLED() {
        return mockMonetization();
    },
}));

// Mock InterestGate so we can assert it's shown when monetization is off
vi.mock('@/components/InterestGate', () => ({
    InterestGate: ({ featureKey }: { featureKey: string }) => (
        <div data-testid="interest-gate" data-feature={featureKey}>
            interest-gate
        </div>
    ),
}));

vi.mock('@/components/TierComparison', () => ({
    TierComparison: () => <div data-testid="tier-comparison" />,
}));

// Pull in the page after mocks are registered
import BillingPage from '@/app/cuenta/billing/page';

describe('/cuenta/billing', () => {
    beforeEach(() => {
        mockUseAuth.mockReset();
        mockMonetization.mockReset();
        mockMonetization.mockReturnValue(false);
        vi.spyOn(global, 'fetch').mockResolvedValue({
            ok: true,
            json: async () => ({ invoices: [] }),
        } as Response);
    });

    describe('when MONETIZATION_ENABLED=false (pre-monetization)', () => {
        beforeEach(() => {
            mockMonetization.mockReturnValue(false);
            mockUseAuth.mockReturnValue(
                mockAuth({ isAuthenticated: true, tier: 'free_member' }),
            );
        });

        it('renders the InterestGate fallback with featureKey="billing"', () => {
            render(<BillingPage />);
            const gate = screen.getByTestId('interest-gate');
            expect(gate).toBeInTheDocument();
            expect(gate.dataset.feature).toBe('billing');
        });

        it('does not call Dhanam invoice API', () => {
            render(<BillingPage />);
            expect(global.fetch).not.toHaveBeenCalled();
        });

        it('shows the Spanish "billing not yet active" copy', () => {
            render(<BillingPage />);
            expect(screen.getByText(/aún no está activa/i)).toBeInTheDocument();
        });
    });

    describe('when MONETIZATION_ENABLED=true and user is unpaid', () => {
        beforeEach(() => {
            mockMonetization.mockReturnValue(true);
            mockUseAuth.mockReturnValue(
                mockAuth({ isAuthenticated: true, tier: 'free_member' }),
            );
        });

        it('shows TierComparison upgrade prompt', () => {
            render(<BillingPage />);
            expect(screen.getByTestId('tier-comparison')).toBeInTheDocument();
        });

        it('does NOT show the customer portal link (user has no paid tier)', () => {
            render(<BillingPage />);
            expect(screen.queryByText(/portal de cliente/i)).not.toBeInTheDocument();
        });

        it('does NOT fetch invoices for unpaid user', () => {
            render(<BillingPage />);
            expect(global.fetch).not.toHaveBeenCalled();
        });
    });

    describe('when MONETIZATION_ENABLED=true and user has paid tier', () => {
        beforeEach(() => {
            mockMonetization.mockReturnValue(true);
            mockUseAuth.mockReturnValue(
                mockAuth({
                    isAuthenticated: true,
                    tier: 'essentials',
                    userId: 'user-123',
                }),
            );
        });

        it('renders the customer portal CTA', () => {
            render(<BillingPage />);
            expect(screen.getByText(/portal de cliente/i)).toBeInTheDocument();
        });

        it('fetches invoices from Dhanam scoped to the current user', async () => {
            render(<BillingPage />);
            await waitFor(() => {
                expect(global.fetch).toHaveBeenCalled();
            });
            const fetchedUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
            expect(fetchedUrl).toContain('/v1/invoices');
            expect(fetchedUrl).toContain('product=tezca');
            expect(fetchedUrl).toContain('user_id=user-123');
        });

        it('renders the empty-state message when Dhanam returns no invoices', async () => {
            render(<BillingPage />);
            await waitFor(() => {
                expect(
                    screen.getByText(/Sin facturas aún|No invoices yet/i),
                ).toBeInTheDocument();
            });
        });

        it('renders an invoice row when Dhanam returns one', async () => {
            (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
                ok: true,
                json: async () => ({
                    invoices: [
                        {
                            id: 'inv_1',
                            issued_at: '2026-04-01T00:00:00Z',
                            amount_mxn: 599,
                            status: 'paid',
                            pdf_url: 'https://example.test/invoice.pdf',
                            cfdi_xml_url: 'https://example.test/cfdi.xml',
                        },
                    ],
                }),
            } as Response);

            render(<BillingPage />);
            await waitFor(() => {
                expect(screen.getByText('PDF')).toBeInTheDocument();
                expect(screen.getByText('CFDI 4.0')).toBeInTheDocument();
            });
        });

        it('handles Dhanam API failure gracefully (empty state, no crash)', async () => {
            (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
                new Error('network'),
            );
            render(<BillingPage />);
            await waitFor(() => {
                expect(
                    screen.getByText(/Sin facturas aún|No invoices yet/i),
                ).toBeInTheDocument();
            });
        });
    });
});
