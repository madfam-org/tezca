import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

const mockUseLang = vi.fn();
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: () => mockUseLang(),
}));

import { HomeHeadings } from '@/components/HomeHeadings';

describe('HomeHeadings', () => {
    it('renders heading in Spanish by default', () => {
        mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
        render(<HomeHeadings />);
        expect(screen.getByText('Explorar por Jurisdicción')).toBeInTheDocument();
    });

    it('renders heading in English', () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(<HomeHeadings />);
        expect(screen.getByText('Explore by Jurisdiction')).toBeInTheDocument();
    });

    it('renders heading in Nahuatl', () => {
        mockUseLang.mockReturnValue({ lang: 'nah', setLang: vi.fn() });
        render(<HomeHeadings />);
        expect(screen.getByText('Xictlachiya ic Tēyācanaliztli')).toBeInTheDocument();
    });
});
