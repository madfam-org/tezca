import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

import { GraphStats } from '@/components/graph/GraphStats';

const SAMPLE: any = {
    nodes: [
        { id: 'a', label: 'Law A', ref_count: 5 },
        { id: 'b', label: 'Law B', ref_count: 10 },
        { id: 'c', label: 'Law C', ref_count: 3 },
    ],
    edges: [
        { source: 'a', target: 'b', weight: 1 },
        { source: 'b', target: 'c', weight: 2 },
    ],
    stats: { total_nodes: 3, total_edges: 2 },
};

describe('GraphStats', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    it('renders the toggle button collapsed by default', () => {
        render(<GraphStats data={SAMPLE} />);
        expect(screen.getByText('Estadísticas')).toBeInTheDocument();
        // Collapsed: stats body not visible
        expect(screen.queryByText('Nodos')).not.toBeInTheDocument();
    });

    it('expands when toggle is clicked', () => {
        render(<GraphStats data={SAMPLE} />);
        fireEvent.click(screen.getByText('Estadísticas'));
        expect(screen.getByText('Nodos')).toBeInTheDocument();
        expect(screen.getByText('Aristas')).toBeInTheDocument();
    });

    it('renders the node + edge counts', () => {
        render(<GraphStats data={SAMPLE} />);
        fireEvent.click(screen.getByText('Estadísticas'));
        expect(screen.getByText('3')).toBeInTheDocument(); // nodes
        expect(screen.getByText('2')).toBeInTheDocument(); // edges
    });

    it('renders the most-connected node label', () => {
        render(<GraphStats data={SAMPLE} />);
        fireEvent.click(screen.getByText('Estadísticas'));
        // Law B has the highest ref_count (10)
        expect(screen.getByText('Law B')).toBeInTheDocument();
    });

    it('computes avg connections', () => {
        render(<GraphStats data={SAMPLE} />);
        fireEvent.click(screen.getByText('Estadísticas'));
        // avg = (5 + 10 + 3) / 3 = 6.0
        expect(screen.getByText('6.0')).toBeInTheDocument();
    });

    it('handles empty graph', () => {
        const empty: any = { nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } };
        render(<GraphStats data={empty} />);
        fireEvent.click(screen.getByText('Estadísticas'));
        // avg = '0', density = '0'
        const zeros = screen.getAllByText('0');
        expect(zeros.length).toBeGreaterThanOrEqual(2);
    });

    it('renders English labels', () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(<GraphStats data={SAMPLE} />);
        fireEvent.click(screen.getByText('Statistics'));
        expect(screen.getByText('Nodes')).toBeInTheDocument();
        expect(screen.getByText('Edges')).toBeInTheDocument();
    });

    it('applies floating wrapper when floating=true', () => {
        const { container } = render(<GraphStats data={SAMPLE} floating />);
        expect(container.firstChild).toHaveClass('absolute');
    });
});
