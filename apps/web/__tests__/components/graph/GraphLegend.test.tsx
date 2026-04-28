import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

import { GraphLegend } from '@/components/graph/GraphLegend';

describe('GraphLegend', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    it('renders the color-mode toggle', () => {
        render(
            <GraphLegend colorMode="category" onColorModeChange={() => {}} />,
        );
        expect(screen.getByText('Categoría')).toBeInTheDocument();
        expect(screen.getByText('Nivel')).toBeInTheDocument();
    });

    it('marks the active mode with the primary color', () => {
        render(
            <GraphLegend colorMode="tier" onColorModeChange={() => {}} />,
        );
        expect(screen.getByText('Nivel').className).toMatch(/bg-primary/);
    });

    it('calls onColorModeChange when toggling mode', () => {
        const onChange = vi.fn();
        render(
            <GraphLegend colorMode="category" onColorModeChange={onChange} />,
        );
        fireEvent.click(screen.getByText('Nivel'));
        expect(onChange).toHaveBeenCalledWith('tier');
    });

    it('renders tier legend items when colorMode=tier', () => {
        render(
            <GraphLegend colorMode="tier" onColorModeChange={() => {}} />,
        );
        // Tier labels include "Federal", "Estatal", "Municipal" or similar
        const swatches = document.querySelectorAll('span.inline-block.rounded-full');
        expect(swatches.length).toBeGreaterThan(0);
    });

    it('renders custom categories when provided', () => {
        render(
            <GraphLegend
                colorMode="category"
                onColorModeChange={() => {}}
                categories={['fiscal', 'labor']}
            />,
        );
        // 2 mode-toggle buttons + 2 category swatches (clickable when onToggle present)
        const swatches = document.querySelectorAll('span.inline-block.rounded-full');
        expect(swatches.length).toBeGreaterThanOrEqual(2);
    });

    it('renders English labels when lang is en', () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(
            <GraphLegend colorMode="category" onColorModeChange={() => {}} />,
        );
        expect(screen.getByText('Color by:')).toBeInTheDocument();
        expect(screen.getByText('Category')).toBeInTheDocument();
        expect(screen.getByText('Tier')).toBeInTheDocument();
    });

    it('applies floating wrapper class when floating=true', () => {
        const { container } = render(
            <GraphLegend colorMode="category" onColorModeChange={() => {}} floating />,
        );
        expect(container.firstChild).toHaveClass('absolute');
    });
});
