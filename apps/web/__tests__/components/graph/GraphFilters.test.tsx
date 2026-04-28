import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

import { GraphFilters } from '@/components/graph/GraphFilters';

describe('GraphFilters', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    it('renders the "all" button + one button per category', () => {
        render(
            <GraphFilters
                categories={['fiscal', 'labor']}
                hiddenCategories={new Set()}
                onToggleCategory={() => {}}
                onShowAll={() => {}}
            />,
        );
        // "Todas" button + 2 category buttons
        expect(screen.getAllByRole('button')).toHaveLength(3);
    });

    it('marks the "all" button as active when no categories are hidden', () => {
        render(
            <GraphFilters
                categories={['fiscal']}
                hiddenCategories={new Set()}
                onToggleCategory={() => {}}
                onShowAll={() => {}}
            />,
        );
        const allButton = screen.getByText('Todas');
        expect(allButton.className).toMatch(/bg-primary/);
    });

    it('invokes onShowAll when the all button is clicked', () => {
        const onShowAll = vi.fn();
        render(
            <GraphFilters
                categories={['fiscal']}
                hiddenCategories={new Set()}
                onToggleCategory={() => {}}
                onShowAll={onShowAll}
            />,
        );
        fireEvent.click(screen.getByText('Todas'));
        expect(onShowAll).toHaveBeenCalledOnce();
    });

    it('invokes onToggleCategory when a category button is clicked', () => {
        const onToggle = vi.fn();
        render(
            <GraphFilters
                categories={['fiscal']}
                hiddenCategories={new Set()}
                onToggleCategory={onToggle}
                onShowAll={() => {}}
            />,
        );
        // Find the second button (the category one)
        const buttons = screen.getAllByRole('button');
        fireEvent.click(buttons[1]);
        expect(onToggle).toHaveBeenCalledWith('fiscal');
    });

    it('renders English labels when lang is en', () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(
            <GraphFilters
                categories={[]}
                hiddenCategories={new Set()}
                onToggleCategory={() => {}}
                onShowAll={() => {}}
            />,
        );
        expect(screen.getByText('Categories:')).toBeInTheDocument();
        expect(screen.getByText('All')).toBeInTheDocument();
    });

    it('applies floating wrapper class when floating=true', () => {
        const { container } = render(
            <GraphFilters
                categories={[]}
                hiddenCategories={new Set()}
                onToggleCategory={() => {}}
                onShowAll={() => {}}
                floating
            />,
        );
        expect(container.firstChild).toHaveClass('absolute');
    });

    it('applies dimmed style to hidden categories', () => {
        render(
            <GraphFilters
                categories={['fiscal']}
                hiddenCategories={new Set(['fiscal'])}
                onToggleCategory={() => {}}
                onShowAll={() => {}}
            />,
        );
        const buttons = screen.getAllByRole('button');
        // Second button = the category, should have the muted-text class
        expect(buttons[1].className).toMatch(/text-muted-foreground\/50/);
    });
});
