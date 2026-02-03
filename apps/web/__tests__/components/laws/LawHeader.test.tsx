import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LawHeader } from '@/components/laws/LawHeader';

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
        render(<LawHeader law={mockLaw} version={mockVersion} />);
        expect(screen.getByText('Ley de Prueba')).toBeInTheDocument();
    });

    it('renders badges correctly', () => {
        render(<LawHeader law={mockLaw} version={mockVersion} />);
        expect(screen.getByText('Federal')).toBeInTheDocument();
        expect(screen.getByText('ley')).toBeInTheDocument();
    });

    it('renders publication date when provided', () => {
        render(<LawHeader law={mockLaw} version={mockVersion} />);
        expect(screen.getByText(/Publicado:/)).toBeInTheDocument();
    });

    it('renders DOF link when provided', () => {
        render(<LawHeader law={mockLaw} version={mockVersion} />);
        const link = screen.getByText('Ver documento original').closest('a');
        expect(link).toHaveAttribute('href', 'https://example.com');
    });
});
