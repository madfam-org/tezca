import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

import { QuickLinks } from '@/components/QuickLinks';

describe('QuickLinks', () => {
    it('renders section title', () => {
        render(<QuickLinks />);
        expect(screen.getByText('Explora la legislación')).toBeInTheDocument();
    });

    it('renders all 4 quick links', () => {
        render(<QuickLinks />);
        expect(screen.getByText('Por Categoría')).toBeInTheDocument();
        expect(screen.getByText('Por Estado')).toBeInTheDocument();
        expect(screen.getByText('Catálogo Completo')).toBeInTheDocument();
        expect(screen.getByText('Búsqueda Avanzada')).toBeInTheDocument();
    });

    it('links to correct pages', () => {
        render(<QuickLinks />);

        expect(screen.getByText('Por Categoría').closest('a')?.getAttribute('href')).toBe('/categorias');
        expect(screen.getByText('Por Estado').closest('a')?.getAttribute('href')).toBe('/estados');
        expect(screen.getByText('Catálogo Completo').closest('a')?.getAttribute('href')).toBe('/leyes');
        expect(screen.getByText('Búsqueda Avanzada').closest('a')?.getAttribute('href')).toBe('/busqueda');
    });

    it('shows descriptions for each link', () => {
        render(<QuickLinks />);
        expect(screen.getByText('Civil, penal, mercantil, fiscal...')).toBeInTheDocument();
        expect(screen.getByText('32 entidades federativas')).toBeInTheDocument();
        expect(screen.getByText('Todas las leyes indexadas')).toBeInTheDocument();
        expect(screen.getByText('Filtros, facetas y texto completo')).toBeInTheDocument();
    });
});
