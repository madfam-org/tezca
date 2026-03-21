import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => <div data-testid="card" className={className}>{children}</div>,
    CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

import { StateCoverageTable } from '@/components/coverage/StateCoverageTable';

const MOCK_STATES = [
    { state: 'Jalisco', legislative: 500, non_legislative: 200, total: 700 },
    { state: 'Aguascalientes', legislative: 300, non_legislative: 100, total: 400 },
    { state: 'Zacatecas', legislative: 150, non_legislative: 50, total: 200 },
];

describe('StateCoverageTable', () => {
    it('renders state rows', () => {
        render(<StateCoverageTable states={MOCK_STATES} lang="es" />);

        expect(screen.getByText('Jalisco')).toBeInTheDocument();
        expect(screen.getByText('Aguascalientes')).toBeInTheDocument();
        expect(screen.getByText('Zacatecas')).toBeInTheDocument();
    });

    it('shows footer totals', () => {
        render(<StateCoverageTable states={MOCK_STATES} lang="es" />);

        // Total legislative: 500 + 300 + 150 = 950
        expect(screen.getByText('950')).toBeInTheDocument();
        // Total non-legislative: 200 + 100 + 50 = 350
        expect(screen.getByText('350')).toBeInTheDocument();
        // Total all: 700 + 400 + 200 = 1,300
        expect(screen.getByText('1,300')).toBeInTheDocument();
    });

    it('sorts by clicking column header', () => {
        render(<StateCoverageTable states={MOCK_STATES} lang="es" />);

        // Click Total header to sort by total descending
        const totalHeader = screen.getByRole('columnheader', { name: /Total/i });
        fireEvent.click(totalHeader);

        const rows = screen.getAllByRole('row');
        // First data row (index 1, after header) should be Jalisco (700) after desc sort
        // Default sort is state ascending, clicking Total switches to total, default desc for numeric
        const cells = rows[1].querySelectorAll('td');
        expect(cells[0].textContent).toBe('Jalisco');
    });

    it('renders trilingual column headers in English', () => {
        render(<StateCoverageTable states={MOCK_STATES} lang="en" />);

        expect(screen.getByText('Coverage by state (3)')).toBeInTheDocument();
        expect(screen.getByRole('columnheader', { name: /State/ })).toBeInTheDocument();
        expect(screen.getByRole('columnheader', { name: /Legislative/ })).toBeInTheDocument();
    });

    it('returns null for empty states', () => {
        const { container } = render(<StateCoverageTable states={[]} lang="es" />);
        expect(container.innerHTML).toBe('');
    });
});
