import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

const mockClearSelection = vi.fn();
let mockSelectedLaws: string[] = [];

vi.mock('./../../components/providers/ComparisonContext', () => ({
    useComparison: () => ({
        selectedLaws: mockSelectedLaws,
        clearSelection: mockClearSelection,
        isLawSelected: vi.fn(),
        toggleLaw: vi.fn(),
    }),
}));

import ComparisonFloatingBar from '@/components/ComparisonFloatingBar';

describe('ComparisonFloatingBar', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockSelectedLaws = [];
    });

    it('returns null when no laws are selected', () => {
        mockSelectedLaws = [];
        const { container } = render(<ComparisonFloatingBar />);
        expect(container.innerHTML).toBe('');
    });

    it('shows the bar when laws are selected', () => {
        mockSelectedLaws = ['law-1'];
        render(<ComparisonFloatingBar />);
        expect(screen.getByText('1 leyes seleccionadas')).toBeInTheDocument();
    });

    it('shows count for multiple selected laws', () => {
        mockSelectedLaws = ['law-1', 'law-2'];
        render(<ComparisonFloatingBar />);
        expect(screen.getByText('2 leyes seleccionadas')).toBeInTheDocument();
    });

    it('renders Limpiar button that calls clearSelection', () => {
        mockSelectedLaws = ['law-1'];
        render(<ComparisonFloatingBar />);
        const clearButton = screen.getByText('Limpiar');
        fireEvent.click(clearButton);
        expect(mockClearSelection).toHaveBeenCalledOnce();
    });

    it('renders Comparar Leyes link', () => {
        mockSelectedLaws = ['law-1', 'law-2'];
        render(<ComparisonFloatingBar />);
        const compareLink = screen.getByText('Comparar Leyes');
        expect(compareLink).toBeInTheDocument();
    });

    it('compare link has correct href with selected law ids', () => {
        mockSelectedLaws = ['law-1', 'law-2'];
        render(<ComparisonFloatingBar />);
        const compareLink = screen.getByText('Comparar Leyes').closest('a');
        expect(compareLink).toHaveAttribute('href', '/comparar?laws=law-1,law-2');
    });

    it('shows select another hint when only one law selected', () => {
        mockSelectedLaws = ['law-1'];
        render(<ComparisonFloatingBar />);
        expect(screen.getByText('Selecciona otra para comparar')).toBeInTheDocument();
    });

    it('hides select another hint when two laws selected', () => {
        mockSelectedLaws = ['law-1', 'law-2'];
        render(<ComparisonFloatingBar />);
        expect(screen.queryByText('Selecciona otra para comparar')).not.toBeInTheDocument();
    });
});
