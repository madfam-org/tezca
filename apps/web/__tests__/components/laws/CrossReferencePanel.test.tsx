import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CrossReferencePanel } from '@/components/laws/CrossReferencePanel';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { makeRefStats } from '../../fixtures/mockFactories';

// Mock global fetch (this component uses raw fetch, not api module)
const mockFetch = vi.fn();
global.fetch = mockFetch;

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe('CrossReferencePanel', () => {
    beforeEach(() => {
        mockFetch.mockReset();
    });

    it('renders loading skeleton initially', () => {
        mockFetch.mockReturnValue(new Promise(() => {}));
        const { container } = renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        expect(container.querySelector('.animate-pulse')).not.toBeNull();
    });

    it('renders nothing when no references', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                statistics: { total_outgoing: 0, total_incoming: 0, most_referenced_laws: [], most_citing_laws: [] },
            }),
        });

        const { container } = renderWithLang(<CrossReferencePanel lawId="empty-law" />);

        await waitFor(() => {
            expect(container.querySelector('.animate-pulse')).toBeNull();
        });

        expect(screen.queryByText('Referencias Cruzadas')).not.toBeInTheDocument();
    });

    it('renders outgoing references with counts', async () => {
        const stats = makeRefStats(3, 0);
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ statistics: stats }),
        });

        renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Referencias Cruzadas')).toBeInTheDocument();
            expect(screen.getByText('Leyes referenciadas')).toBeInTheDocument();
        });

        // All 3 outgoing refs should show
        expect(screen.getByText('ley-a')).toBeInTheDocument();
        expect(screen.getByText('ley-b')).toBeInTheDocument();
        expect(screen.getByText('ley-c')).toBeInTheDocument();
    });

    it('renders incoming references with counts', async () => {
        const stats = makeRefStats(0, 3);
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ statistics: stats }),
        });

        renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Leyes que citan esta')).toBeInTheDocument();
        });

        expect(screen.getByText('ley-citante-1')).toBeInTheDocument();
        expect(screen.getByText('ley-citante-2')).toBeInTheDocument();
    });

    it('truncates to 5 items by default', async () => {
        const stats = makeRefStats(8, 0);
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ statistics: stats }),
        });

        renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('ley-a')).toBeInTheDocument();
        });

        // Only first 5 should show
        expect(screen.getByText('ley-e')).toBeInTheDocument();
        expect(screen.queryByText('ley-f')).not.toBeInTheDocument();
    });

    it('expand button shows all references', async () => {
        const user = userEvent.setup();
        const stats = makeRefStats(8, 0);
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ statistics: stats }),
        });

        renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText(/Ver todas/)).toBeInTheDocument();
        });

        await user.click(screen.getByText(/Ver todas/));

        // Now all 8 should be visible
        expect(screen.getByText('ley-f')).toBeInTheDocument();
        expect(screen.getByText('ley-g')).toBeInTheDocument();
        expect(screen.getByText('ley-h')).toBeInTheDocument();
    });

    it('renders links to law pages', async () => {
        const stats = makeRefStats(2, 0);
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ statistics: stats }),
        });

        renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        await waitFor(() => {
            const link = screen.getByText('ley-a').closest('a');
            expect(link).toHaveAttribute('href', '/leyes/ley-a');
        });
    });

    it('handles API failure gracefully', async () => {
        mockFetch.mockResolvedValue({ ok: false, status: 500 });

        const { container } = renderWithLang(<CrossReferencePanel lawId="bad-law" />);

        await waitFor(() => {
            expect(container.querySelector('.animate-pulse')).toBeNull();
        });

        // Should not crash, should not show panel
        expect(screen.queryByText('Referencias Cruzadas')).not.toBeInTheDocument();
    });

    it('handles slugs with special characters', async () => {
        const stats = {
            total_outgoing: 1,
            total_incoming: 0,
            most_referenced_laws: [{ slug: 'ley-org\u00e1nica_pjf-2024', count: 5 }],
            most_citing_laws: [],
        };
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ statistics: stats }),
        });

        renderWithLang(<CrossReferencePanel lawId="cpeum" />);

        await waitFor(() => {
            const link = screen.getByText('ley-org\u00e1nica_pjf-2024').closest('a');
            expect(link).toHaveAttribute('href', '/leyes/ley-org\u00e1nica_pjf-2024');
        });
    });
});
