import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LawCard from '@/components/LawCard';

// Mock ComparisonContext
vi.mock('@/components/providers/ComparisonContext', () => ({
    useComparison: () => ({
        selectedLaws: [],
        toggleLaw: vi.fn(),
        isLawSelected: () => false,
        clearSelection: vi.fn(),
    }),
}));

describe('LawCard', () => {
    const mockLaw = {
        id: 'ley-de-amparo',
        name: 'Ley de Amparo',
        grade: 'A' as const,
        priority: 1,
        articles: 271,
        score: 98.5,
        transitorios: 12,
    };

    it('renders law name', () => {
        render(<LawCard law={mockLaw} />);
        expect(screen.getByText('Ley de Amparo')).toBeInTheDocument();
    });

    it('renders grade badge', () => {
        render(<LawCard law={mockLaw} />);
        expect(screen.getByText('Grade A')).toBeInTheDocument();
    });

    it('renders article count and score', () => {
        render(<LawCard law={mockLaw} />);
        expect(screen.getByText('271')).toBeInTheDocument();
        expect(screen.getByText('98.5%')).toBeInTheDocument();
    });

    it('renders transitorios count when present', () => {
        render(<LawCard law={mockLaw} />);
        expect(screen.getByText('+ 12 transitorios')).toBeInTheDocument();
    });

    it('does not render transitorios when zero', () => {
        render(<LawCard law={{ ...mockLaw, transitorios: 0 }} />);
        expect(screen.queryByText(/transitorios/)).not.toBeInTheDocument();
    });

    it('generates correct link to law detail', () => {
        render(<LawCard law={mockLaw} />);
        const link = screen.getByRole('link');
        expect(link).toHaveAttribute('href', '/laws/ley-de-amparo');
    });

    it('renders priority badge', () => {
        render(<LawCard law={mockLaw} />);
        expect(screen.getByText('Prioridad 1')).toBeInTheDocument();
    });
});
