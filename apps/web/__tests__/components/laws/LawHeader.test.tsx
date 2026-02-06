import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LawHeader } from '@/components/laws/LawHeader';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { BookmarksProvider } from '@/components/providers/BookmarksContext';

function renderWithProviders(ui: React.ReactElement) {
    return render(
        <LanguageProvider>
            <BookmarksProvider>{ui}</BookmarksProvider>
        </LanguageProvider>
    );
}

describe('LawHeader', () => {
    const mockLaw = {
        official_id: 'test_law',
        name: 'Ley de Prueba',
        category: 'ley',
        tier: 'federal',
        state: null,
    };

    const mockVersion = {
        publication_date: '2024-01-01',
        dof_url: 'https://example.com',
    };

    it('renders law name correctly', () => {
        renderWithProviders(<LawHeader law={mockLaw} version={mockVersion} />);
        expect(screen.getByText('Ley de Prueba')).toBeInTheDocument();
    });

    it('renders badges correctly', () => {
        renderWithProviders(<LawHeader law={mockLaw} version={mockVersion} />);
        expect(screen.getByText('Federal')).toBeInTheDocument();
        expect(screen.getByText('ley')).toBeInTheDocument();
    });

    it('renders publication date when provided', () => {
        renderWithProviders(<LawHeader law={mockLaw} version={mockVersion} />);
        expect(screen.getByText(/Publicado:|Published:/)).toBeInTheDocument();
    });

    it('renders DOF link when provided', () => {
        renderWithProviders(<LawHeader law={mockLaw} version={mockVersion} />);
        const link = screen.getByText(/Ver documento original|View original document/).closest('a');
        expect(link).toHaveAttribute('href', 'https://example.com');
    });
});
