import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TableOfContents } from '@/components/laws/TableOfContents';
import type { Article } from '@/components/laws/types';

describe('TableOfContents', () => {
    const mockArticles: Article[] = [
        { article_id: '1', text: 'Artículo primero...' },
        { article_id: '2', text: 'Artículo segundo...' },
        { article_id: '3', text: 'Artículo tercero...' },
    ];

    const mockOnClick = vi.fn();

    afterEach(() => {
        mockOnClick.mockClear();
    });

    it('renders header', () => {
        render(
            <TableOfContents articles={mockArticles} activeArticle={null} onArticleClick={mockOnClick} />
        );
        expect(screen.getByText('Tabla de Contenidos')).toBeInTheDocument();
    });

    it('renders article buttons', () => {
        render(
            <TableOfContents articles={mockArticles} activeArticle={null} onArticleClick={mockOnClick} />
        );

        expect(screen.getByText('Artículo 1')).toBeInTheDocument();
        expect(screen.getByText('Artículo 2')).toBeInTheDocument();
        expect(screen.getByText('Artículo 3')).toBeInTheDocument();
    });

    it('shows empty state when no articles', () => {
        render(
            <TableOfContents articles={[]} activeArticle={null} onArticleClick={mockOnClick} />
        );

        expect(screen.getByText('No se encontraron artículos.')).toBeInTheDocument();
    });

    it('renders article count', () => {
        render(
            <TableOfContents articles={mockArticles} activeArticle={null} onArticleClick={mockOnClick} />
        );

        expect(screen.getByText('3 elementos')).toBeInTheDocument();
    });

    it('calls onArticleClick with correct ID', () => {
        render(
            <TableOfContents articles={mockArticles} activeArticle={null} onArticleClick={mockOnClick} />
        );

        fireEvent.click(screen.getByText('Artículo 2'));
        expect(mockOnClick).toHaveBeenCalledWith('2');
    });

    it('highlights active article', () => {
        render(
            <TableOfContents articles={mockArticles} activeArticle="2" onArticleClick={mockOnClick} />
        );

        const activeButton = screen.getByText('Artículo 2').closest('button');
        expect(activeButton).toHaveClass('bg-primary/10');
        expect(activeButton).toHaveClass('text-primary');
    });

    it('displays "Texto Completo" for texto_completo article_id', () => {
        const articles: Article[] = [
            { article_id: 'texto_completo', text: 'Full text...' },
        ];

        render(
            <TableOfContents articles={articles} activeArticle={null} onArticleClick={mockOnClick} />
        );

        expect(screen.getByText('Texto Completo')).toBeInTheDocument();
    });

    it('shows zero count for empty articles', () => {
        render(
            <TableOfContents articles={[]} activeArticle={null} onArticleClick={mockOnClick} />
        );

        expect(screen.getByText('0 elementos')).toBeInTheDocument();
    });
});
