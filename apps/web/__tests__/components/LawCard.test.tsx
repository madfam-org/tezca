import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LawCard from '@/components/LawCard';
import { LanguageProvider } from '@/components/providers/LanguageContext';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

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
        renderWithLang(<LawCard law={mockLaw} />);
        expect(screen.getByText('Ley de Amparo')).toBeInTheDocument();
    });

    it('renders grade badge', () => {
        renderWithLang(<LawCard law={mockLaw} />);
        expect(screen.getByText('Grado A')).toBeInTheDocument();
    });

    it('renders article count and score', () => {
        renderWithLang(<LawCard law={mockLaw} />);
        expect(screen.getByText('271')).toBeInTheDocument();
        expect(screen.getByText('98.5%')).toBeInTheDocument();
    });

    it('renders transitorios count when present', () => {
        renderWithLang(<LawCard law={mockLaw} />);
        expect(screen.getByText('+ 12 transitorios')).toBeInTheDocument();
    });

    it('does not render transitorios when zero', () => {
        renderWithLang(<LawCard law={{ ...mockLaw, transitorios: 0 }} />);
        expect(screen.queryByText(/transitorios/)).not.toBeInTheDocument();
    });

    it('generates correct link to law detail', () => {
        renderWithLang(<LawCard law={mockLaw} />);
        const link = screen.getByRole('link');
        expect(link).toHaveAttribute('href', '/leyes/ley-de-amparo');
    });

    it('renders priority badge', () => {
        renderWithLang(<LawCard law={mockLaw} />);
        expect(screen.getByText('Prioridad 1')).toBeInTheDocument();
    });
});
