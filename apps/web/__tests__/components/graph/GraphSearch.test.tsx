import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

const mockTrackEvent = vi.fn();
vi.mock('@/lib/analytics/posthog', () => ({
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

import { GraphSearch } from '@/components/graph/GraphSearch';

const NODES = [
    { id: 'cpeum', label: 'Constitución Política' },
    { id: 'amparo', label: 'Ley de Amparo' },
    { id: 'civil', label: 'Código Civil Federal' },
];

describe('GraphSearch', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    it('renders the input with i18n placeholder', () => {
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={() => {}} />);
        expect(screen.getByPlaceholderText('Buscar ley...')).toBeInTheDocument();
    });

    it('does not show suggestions when query is shorter than 2 chars', () => {
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={() => {}} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        fireEvent.change(input, { target: { value: 'C' } });
        expect(screen.queryByText('Constitución Política')).not.toBeInTheDocument();
    });

    it('shows matching suggestions when query is ≥2 chars', () => {
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={() => {}} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        // "ons" matches "Constitución" ("ons" in "constitución") via includes
        fireEvent.change(input, { target: { value: 'ons' } });
        expect(screen.getByText('Constitución Política')).toBeInTheDocument();
    });

    it('calls onFocus + tracks event on suggestion click', () => {
        const onFocus = vi.fn();
        render(<GraphSearch nodes={NODES} onFocus={onFocus} onClear={() => {}} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        fireEvent.change(input, { target: { value: 'Cons' } });
        fireEvent.click(screen.getByText('Constitución Política'));
        expect(onFocus).toHaveBeenCalledWith('cpeum');
        expect(mockTrackEvent).toHaveBeenCalledWith(
            'graph.node_searched',
            expect.objectContaining({ node_id: 'cpeum' }),
        );
    });

    it('shows clear button when query is non-empty + invokes onClear', () => {
        const onClear = vi.fn();
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={onClear} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        fireEvent.change(input, { target: { value: 'X' } });
        fireEvent.click(screen.getByLabelText('Limpiar búsqueda'));
        expect(onClear).toHaveBeenCalledOnce();
        // Input cleared + dropdown closed
        expect((input as HTMLInputElement).value).toBe('');
    });

    it('Escape key clears the search', () => {
        const onClear = vi.fn();
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={onClear} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        fireEvent.change(input, { target: { value: 'Co' } });
        fireEvent.keyDown(input, { key: 'Escape' });
        expect(onClear).toHaveBeenCalledOnce();
    });

    it('Enter selects the highlighted suggestion', () => {
        const onFocus = vi.fn();
        render(<GraphSearch nodes={NODES} onFocus={onFocus} onClear={() => {}} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        fireEvent.change(input, { target: { value: 'Co' } });
        fireEvent.keyDown(input, { key: 'Enter' });
        // First match was "Constitución Política"
        expect(onFocus).toHaveBeenCalledWith('cpeum');
    });

    it('Arrow keys do not crash on empty results', () => {
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={() => {}} />);
        const input = screen.getByPlaceholderText('Buscar ley...');
        // No query → no suggestions
        fireEvent.keyDown(input, { key: 'ArrowDown' });
        fireEvent.keyDown(input, { key: 'ArrowUp' });
        // Just verify nothing crashed
        expect(input).toBeInTheDocument();
    });

    it('uses English placeholder when lang is en', () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        render(<GraphSearch nodes={NODES} onFocus={() => {}} onClear={() => {}} />);
        expect(screen.getByPlaceholderText('Search law...')).toBeInTheDocument();
    });
});
