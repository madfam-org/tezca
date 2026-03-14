import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
    LOCALE_MAP: { es: 'es-MX', en: 'en-US', nah: 'es-MX' },
}));

const mockGetStats = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        getStats: (...args: any[]) => mockGetStats(...args),
    },
}));

import { DynamicFeatures } from '@/components/DynamicFeatures';
import { useLang } from '@/components/providers/LanguageContext';

const MOCK_STATS = {
    total_laws: 35000,
    federal_count: 2000,
    state_count: 30000,
    municipal_count: 3000,
    legislative_count: 20000,
    non_legislative_count: 15000,
    total_articles: 1071445,
    federal_coverage: 90,
    state_coverage: 85,
    municipal_coverage: 30,
    total_coverage: 75,
    last_update: '2026-03-01',
    recent_laws: [],
    coverage: {
        leyes_vigentes: { count: 35000, universe: 45000, percentage: 78 },
        federal: { count: 2000, universe: 2500, percentage: 80 },
        state: { count: 30000, universe: 35000, percentage: 86 },
        municipal: { count: 3000, universe: null, percentage: null },
    },
};

describe('DynamicFeatures', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    // ---------------------------------------------------------------
    // 1. Shows loading skeletons
    // ---------------------------------------------------------------
    it('shows loading skeletons while fetching', () => {
        mockGetStats.mockReturnValue(new Promise(() => {}));
        render(<DynamicFeatures />);

        const pulses = document.querySelectorAll('.animate-pulse');
        expect(pulses.length).toBeGreaterThanOrEqual(1);
    });

    // ---------------------------------------------------------------
    // 2. Renders coverage feature with percentage
    // ---------------------------------------------------------------
    it('renders coverage feature with percentage', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('78% Cobertura Legislativa')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 3. Renders search feature with article count
    // ---------------------------------------------------------------
    it('renders search feature with article count', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('Búsqueda Completa')).toBeInTheDocument();
            expect(screen.getByText(/1,071,445.*artículos indexados/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 4. Renders states feature
    // ---------------------------------------------------------------
    it('renders 32 states feature card', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('32 Estados Cubiertos')).toBeInTheDocument();
            expect(screen.getByText('Legislación de todas las entidades federativas del país')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 5. Shows coverage description
    // ---------------------------------------------------------------
    it('shows coverage description with count/universe/pct', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText(/35,000 de 45,000 leyes vigentes.*78%/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 6. Fallback when coverage is missing
    // ---------------------------------------------------------------
    it('shows fallback when coverage data is missing', async () => {
        const noCoverage = { ...MOCK_STATS, coverage: undefined };
        mockGetStats.mockResolvedValue(noCoverage);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('Cobertura Legal')).toBeInTheDocument();
            expect(screen.getByText(/35,000 leyes digitalizadas/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 7. English labels
    // ---------------------------------------------------------------
    it('renders English labels when lang is en', async () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('Full-Text Search')).toBeInTheDocument();
            expect(screen.getByText('32 States Covered')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 8. Nahuatl labels
    // ---------------------------------------------------------------
    it('renders Nahuatl labels when lang is nah', async () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'nah', setLang: vi.fn() });
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('32 Altepetl')).toBeInTheDocument();
            expect(screen.getByText('Mochi Tlahcuilōlli Tlatemoliztli')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 9. Handles API failure gracefully
    // ---------------------------------------------------------------
    it('handles API failure gracefully without crashing', async () => {
        mockGetStats.mockRejectedValue(new Error('API error'));
        render(<DynamicFeatures />);

        // After error, loading should stop and fallback should render
        await waitFor(() => {
            expect(screen.getByText('Cobertura Legal')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 10. Three feature cards rendered
    // ---------------------------------------------------------------
    it('renders exactly 3 feature cards', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            const headings = document.querySelectorAll('h3');
            expect(headings.length).toBe(3);
        });
    });

    // ---------------------------------------------------------------
    // 11. Coverage percentage clamped to 100
    // ---------------------------------------------------------------
    it('clamps coverage percentage to 100 when count exceeds universe', async () => {
        const overageStats = {
            ...MOCK_STATS,
            coverage: {
                ...MOCK_STATS.coverage,
                leyes_vigentes: { count: 50000, universe: 45000, percentage: 111 },
            },
        };
        mockGetStats.mockResolvedValue(overageStats);
        render(<DynamicFeatures />);

        await waitFor(() => {
            expect(screen.getByText('100% Cobertura Legislativa')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 12. Display universe uses Math.max
    // ---------------------------------------------------------------
    it('displays count as universe when count exceeds universe', async () => {
        const overageStats = {
            ...MOCK_STATS,
            coverage: {
                ...MOCK_STATS.coverage,
                leyes_vigentes: { count: 50000, universe: 45000, percentage: 111 },
            },
        };
        mockGetStats.mockResolvedValue(overageStats);
        render(<DynamicFeatures />);

        await waitFor(() => {
            // displayUniverse = Math.max(50000, 45000) = 50000
            expect(screen.getByText(/50,000 de 50,000 leyes vigentes.*100%/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 13. Feature icons present
    // ---------------------------------------------------------------
    it('renders feature icons', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<DynamicFeatures />);

        await waitFor(() => {
            // Icons are emoji strings rendered in the Feature component
            const container = document.querySelector('.grid');
            expect(container?.textContent).toContain('✨');
            expect(container?.textContent).toContain('🔍');
        });
    });
});
