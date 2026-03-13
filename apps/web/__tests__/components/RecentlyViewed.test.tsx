import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Badge: ({ children, className, ...props }: any) => <span className={className} {...props}>{children}</span>,
    Card: ({ children, className }: any) => <div data-testid="card" className={className}>{children}</div>,
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Clock: ({ className }: any) => <span data-testid="clock-icon" className={className} />,
    ChevronRight: ({ className }: any) => <span data-testid="chevron-icon" className={className} />,
}));

import { RecentlyViewed, recordLawView } from '@/components/RecentlyViewed';
import { useLang } from '@/components/providers/LanguageContext';

const STORAGE_KEY = 'recently-viewed-laws';

describe('RecentlyViewed', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.removeItem(STORAGE_KEY);
    });

    // ---------------------------------------------------------------
    // 1. Returns null when no recent views
    // ---------------------------------------------------------------
    it('renders nothing when there are no recently viewed laws', () => {
        const { container } = render(<RecentlyViewed />);
        expect(container.innerHTML).toBe('');
    });

    // ---------------------------------------------------------------
    // 2. Renders section title when items exist
    // ---------------------------------------------------------------
    it('renders section title when items exist', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'cpeum', name: 'Constitucion', tier: 'federal', viewedAt: '2026-03-01T12:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        expect(screen.getByText('Consultadas recientemente')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Renders law names
    // ---------------------------------------------------------------
    it('renders law names from localStorage', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'cpeum', name: 'Constitucion', tier: 'federal', viewedAt: '2026-03-01T12:00:00Z' },
            { id: 'lft', name: 'Ley Federal del Trabajo', tier: 'federal', viewedAt: '2026-03-01T11:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        expect(screen.getByText('Constitucion')).toBeInTheDocument();
        expect(screen.getByText('Ley Federal del Trabajo')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 4. Renders tier badges
    // ---------------------------------------------------------------
    it('renders tier badges with localized labels', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'cpeum', name: 'Constitucion', tier: 'federal', viewedAt: '2026-03-01T12:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        expect(screen.getByText('Federal')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 5. Links to law detail pages
    // ---------------------------------------------------------------
    it('links to correct law detail pages', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'cpeum', name: 'Constitucion', tier: 'federal', viewedAt: '2026-03-01T12:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        const link = screen.getByText('Constitucion').closest('a');
        expect(link?.getAttribute('href')).toBe('/leyes/cpeum');
    });

    // ---------------------------------------------------------------
    // 6. Shows max 6 items
    // ---------------------------------------------------------------
    it('shows maximum 6 items', () => {
        const items = Array.from({ length: 8 }, (_, i) => ({
            id: `law-${i}`,
            name: `Law ${i}`,
            tier: 'federal',
            viewedAt: new Date(2026, 2, 1, 12, i).toISOString(),
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));

        render(<RecentlyViewed />);
        const cards = screen.getAllByTestId('card');
        expect(cards.length).toBe(6);
    });

    // ---------------------------------------------------------------
    // 7. State tier label in Spanish
    // ---------------------------------------------------------------
    it('shows "Estatal" for state tier in Spanish', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'ccbc', name: 'Codigo Civil BC', tier: 'state', viewedAt: '2026-03-01T12:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        expect(screen.getByText('Estatal')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 8. Municipal tier label
    // ---------------------------------------------------------------
    it('shows "Municipal" for municipal tier', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'ban-gdl', name: 'Bando GDL', tier: 'municipal', viewedAt: '2026-03-01T12:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        expect(screen.getByText('Municipal')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 9. English labels
    // ---------------------------------------------------------------
    it('renders English title and labels when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });
        localStorage.setItem(STORAGE_KEY, JSON.stringify([
            { id: 'cpeum', name: 'Constitution', tier: 'state', viewedAt: '2026-03-01T12:00:00Z' },
        ]));

        render(<RecentlyViewed />);
        expect(screen.getByText('Recently viewed')).toBeInTheDocument();
        expect(screen.getByText('State')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 10. recordLawView adds an entry
    // ---------------------------------------------------------------
    it('recordLawView adds an entry to localStorage', () => {
        recordLawView({ id: 'cpeum', name: 'Constitucion', tier: 'federal' });

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        expect(stored).toHaveLength(1);
        expect(stored[0].id).toBe('cpeum');
        expect(stored[0].viewedAt).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 11. recordLawView deduplicates
    // ---------------------------------------------------------------
    it('recordLawView deduplicates and moves to front', () => {
        recordLawView({ id: 'lft', name: 'LFT', tier: 'federal' });
        recordLawView({ id: 'cpeum', name: 'CPEUM', tier: 'federal' });
        recordLawView({ id: 'lft', name: 'LFT', tier: 'federal' });

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        expect(stored).toHaveLength(2);
        expect(stored[0].id).toBe('lft'); // Most recent first
        expect(stored[1].id).toBe('cpeum');
    });

    // ---------------------------------------------------------------
    // 12. recordLawView caps at 10
    // ---------------------------------------------------------------
    it('recordLawView caps at 10 entries', () => {
        for (let i = 0; i < 15; i++) {
            recordLawView({ id: `law-${i}`, name: `Law ${i}`, tier: 'federal' });
        }

        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        expect(stored).toHaveLength(10);
    });
});
