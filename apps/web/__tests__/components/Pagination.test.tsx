import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Pagination } from '@/components/Pagination';

describe('Pagination', () => {
    const mockOnPageChange = vi.fn();

    afterEach(() => {
        mockOnPageChange.mockClear();
    });

    it('renders nothing when totalPages <= 1', () => {
        const { container } = render(
            <Pagination currentPage={1} totalPages={1} onPageChange={mockOnPageChange} />
        );
        expect(container.firstChild).toBeNull();
    });

    it('renders nothing when totalPages is 0', () => {
        const { container } = render(
            <Pagination currentPage={1} totalPages={0} onPageChange={mockOnPageChange} />
        );
        expect(container.firstChild).toBeNull();
    });

    it('shows all page numbers when totalPages <= 7', () => {
        render(
            <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
        );

        for (let i = 1; i <= 5; i++) {
            expect(screen.getByRole('button', { name: String(i) })).toBeInTheDocument();
        }
    });

    it('disables first/previous buttons on page 1', () => {
        render(
            <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
        );

        expect(screen.getByTitle('Primera página')).toBeDisabled();
        expect(screen.getByTitle('Página anterior')).toBeDisabled();
        expect(screen.getByTitle('Página siguiente')).not.toBeDisabled();
        expect(screen.getByTitle('Última página')).not.toBeDisabled();
    });

    it('disables next/last buttons on last page', () => {
        render(
            <Pagination currentPage={5} totalPages={5} onPageChange={mockOnPageChange} />
        );

        expect(screen.getByTitle('Primera página')).not.toBeDisabled();
        expect(screen.getByTitle('Página anterior')).not.toBeDisabled();
        expect(screen.getByTitle('Página siguiente')).toBeDisabled();
        expect(screen.getByTitle('Última página')).toBeDisabled();
    });

    it('calls onPageChange with correct page on click', () => {
        render(
            <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
        );

        fireEvent.click(screen.getByRole('button', { name: '4' }));
        expect(mockOnPageChange).toHaveBeenCalledWith(4);
    });

    it('calls onPageChange(1) when first page button clicked', () => {
        render(
            <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
        );

        fireEvent.click(screen.getByTitle('Primera página'));
        expect(mockOnPageChange).toHaveBeenCalledWith(1);
    });

    it('calls onPageChange(prev) when previous button clicked', () => {
        render(
            <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
        );

        fireEvent.click(screen.getByTitle('Página anterior'));
        expect(mockOnPageChange).toHaveBeenCalledWith(2);
    });

    it('shows ellipsis for large page counts', () => {
        render(
            <Pagination currentPage={5} totalPages={20} onPageChange={mockOnPageChange} />
        );

        // Should have first page, ellipsis, pages around current, ellipsis, last page
        expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '20' })).toBeInTheDocument();
        expect(screen.getAllByText('...').length).toBeGreaterThanOrEqual(1);
    });

    it('does not show leading ellipsis when near start', () => {
        render(
            <Pagination currentPage={2} totalPages={20} onPageChange={mockOnPageChange} />
        );

        // Near start: 1, 2, 3, ..., 20
        expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '3' })).toBeInTheDocument();
        expect(screen.getAllByText('...')).toHaveLength(1);
    });

    it('applies className prop', () => {
        const { container } = render(
            <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} className="mt-8" />
        );

        expect(container.firstChild).toHaveClass('mt-8');
    });
});
