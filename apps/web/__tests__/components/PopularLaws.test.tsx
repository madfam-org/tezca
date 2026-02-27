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

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Badge: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <span data-testid="badge" className={className}>{children}</span>
    ),
}));

import { PopularLaws } from '@/components/PopularLaws';

describe('PopularLaws', () => {
    it('renders section title', () => {
        render(<PopularLaws />);
        expect(screen.getByText('Leyes Populares')).toBeInTheDocument();
    });

    it('renders subtitle', () => {
        render(<PopularLaws />);
        expect(screen.getByText('Acceso rápido a las leyes más consultadas')).toBeInTheDocument();
    });

    it('renders all 8 popular law badges', () => {
        render(<PopularLaws />);
        expect(screen.getByText('Constitución')).toBeInTheDocument();
        expect(screen.getByText('Código Civil Federal')).toBeInTheDocument();
        expect(screen.getByText('Código Penal Federal')).toBeInTheDocument();
        expect(screen.getByText('ISR')).toBeInTheDocument();
        expect(screen.getByText('IVA')).toBeInTheDocument();
        expect(screen.getByText('Ley Federal del Trabajo')).toBeInTheDocument();
        expect(screen.getByText('Seguro Social')).toBeInTheDocument();
        expect(screen.getByText('Amparo')).toBeInTheDocument();
    });

    it('links to correct law detail pages using short IDs', () => {
        render(<PopularLaws />);

        const expectedLinks = [
            { name: 'Constitución', href: '/leyes/cpeum' },
            { name: 'Código Civil Federal', href: '/leyes/ccf' },
            { name: 'Código Penal Federal', href: '/leyes/cpf' },
            { name: 'ISR', href: '/leyes/lisr' },
            { name: 'IVA', href: '/leyes/liva' },
            { name: 'Ley Federal del Trabajo', href: '/leyes/lft' },
            { name: 'Seguro Social', href: '/leyes/lss' },
            { name: 'Amparo', href: '/leyes/amparo' },
        ];

        for (const { name, href } of expectedLinks) {
            const link = screen.getByText(name).closest('a');
            expect(link?.getAttribute('href')).toBe(href);
        }
    });

    it('does not use mx-fed- prefix in hrefs', () => {
        render(<PopularLaws />);
        const links = screen.getAllByRole('link');
        for (const link of links) {
            expect(link.getAttribute('href')).not.toContain('mx-fed-');
        }
    });

    it('renders 8 badge elements', () => {
        render(<PopularLaws />);
        const badges = screen.getAllByTestId('badge');
        expect(badges).toHaveLength(8);
    });
});
