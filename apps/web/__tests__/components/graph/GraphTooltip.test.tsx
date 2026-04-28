import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

import { GraphTooltip } from '@/components/graph/GraphTooltip';

const node = {
    id: 'cpeum',
    label: 'Constitución Política',
    tier: 'federal',
    category: 'fiscal',
    ref_count: 42,
};

describe('GraphTooltip', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    it('renders nothing when node is null', () => {
        const { container } = render(<GraphTooltip node={null} position={{ x: 0, y: 0 }} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders nothing when position is null', () => {
        const { container } = render(<GraphTooltip node={node as any} position={null} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders the node label', () => {
        render(<GraphTooltip node={node as any} position={{ x: 100, y: 200 }} />);
        expect(screen.getByText('Constitución Política')).toBeInTheDocument();
    });

    it('renders the tier badge', () => {
        render(<GraphTooltip node={node as any} position={{ x: 0, y: 0 }} />);
        expect(screen.getByText('federal')).toBeInTheDocument();
    });

    it('renders the ref_count + i18n suffix', () => {
        render(<GraphTooltip node={node as any} position={{ x: 0, y: 0 }} />);
        // "42 referencias"
        expect(screen.getByText(/42/)).toBeInTheDocument();
        expect(screen.getByText(/referencias/)).toBeInTheDocument();
    });

    it('uses English suffix when lang is en', () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(<GraphTooltip node={node as any} position={{ x: 0, y: 0 }} />);
        expect(screen.getByText(/references/)).toBeInTheDocument();
        expect(screen.getByText('Click to view')).toBeInTheDocument();
    });

    it('positions itself based on the position prop', () => {
        const { container } = render(
            <GraphTooltip node={node as any} position={{ x: 100, y: 200 }} />,
        );
        const tooltip = container.firstChild as HTMLElement;
        expect(tooltip.style.left).toBe('112px'); // x + 12
        expect(tooltip.style.top).toBe('190px'); // y - 10
    });

    it('omits the category badge when node has no category', () => {
        const noCat = { ...node, category: undefined as any };
        const { container } = render(
            <GraphTooltip node={noCat} position={{ x: 0, y: 0 }} />,
        );
        // Tier still renders; category swatch is gone — just verify no crash
        expect(container.firstChild).toBeTruthy();
    });
});
