import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@tezca/ui', () => ({
    Badge: ({ children, className }: any) => <span data-testid="badge" className={className}>{children}</span>,
    Button: ({ children, className, onClick, ...props }: any) => (
        <button className={className} onClick={onClick} {...props}>{children}</button>
    ),
    Card: ({ children, className }: any) => <div data-testid="card" className={className}>{children}</div>,
    CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

import { CoverageViewTabs } from '@/components/coverage/CoverageViewTabs';

const MOCK_VIEWS = {
    leyes_vigentes: {
        label: { es: 'Leyes Legislativas Vigentes', en: 'Active Legislative Laws', nah: 'Tenahuatilli Yancuīc' },
        universe: 12804,
        captured: 12804,
        pct: 100,
    },
    marco_juridico_completo: {
        label: { es: 'Marco Jurídico Completo', en: 'Complete Legal Framework', nah: 'Mochi Tenahuatiliz' },
        universe: 36719,
        captured: 31846,
        pct: 86.7,
    },
    normatividad_primaria: {
        label: { es: 'Normatividad Primaria', en: 'Primary Legislation', nah: 'Tenahuatilli Achto' },
        universe: 36719,
        captured: 34285,
        pct: 93.4,
    },
    marco_juridico_total: {
        label: { es: 'Marco Jurídico Total', en: 'Total Legal Framework', nah: 'Mochi Cemānāhuac Tenahuatilli' },
        universe: 652136,
        captured: 35945,
        pct: 5.5,
    },
};

describe('CoverageViewTabs', () => {
    it('renders 4 view tab buttons', () => {
        render(<CoverageViewTabs views={MOCK_VIEWS} lang="es" />);

        const tabs = screen.getAllByRole('tab');
        expect(tabs).toHaveLength(4);
    });

    it('default active is first view (leyes_vigentes)', () => {
        render(<CoverageViewTabs views={MOCK_VIEWS} lang="es" />);

        // The active detail card shows captured/universe text
        expect(screen.getByText(/12,804 \/ 12,804/)).toBeInTheDocument();
    });

    it('clicking tab changes active view', () => {
        render(<CoverageViewTabs views={MOCK_VIEWS} lang="es" />);

        const tabs = screen.getAllByRole('tab');
        // Click on marco_juridico_total (last tab)
        fireEvent.click(tabs[tabs.length - 1]);

        // Detail card should now show total framework data
        expect(screen.getByText(/35,945 \/ 652,136/)).toBeInTheDocument();
    });

    it('shows percentage badge on each tab', () => {
        render(<CoverageViewTabs views={MOCK_VIEWS} lang="es" />);

        const badges = screen.getAllByTestId('badge');
        expect(badges.length).toBeGreaterThanOrEqual(4);
    });

    it('renders trilingual labels in English', () => {
        render(<CoverageViewTabs views={MOCK_VIEWS} lang="en" />);

        expect(screen.getByText('Coverage perspectives')).toBeInTheDocument();
        // Active Legislative Laws appears in tab + detail
        expect(screen.getAllByText(/Active Legislative Laws/).length).toBeGreaterThanOrEqual(1);
    });

    it('returns null for empty views', () => {
        const { container } = render(<CoverageViewTabs views={{}} lang="es" />);
        expect(container.innerHTML).toBe('');
    });
});
