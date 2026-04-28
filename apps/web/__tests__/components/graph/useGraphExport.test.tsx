import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGraphExport } from '@/components/graph/useGraphExport';

describe('useGraphExport', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns an exportPNG function', () => {
        const { result } = renderHook(() => useGraphExport(() => null));
        expect(typeof result.current.exportPNG).toBe('function');
    });

    it('exportPNG is a no-op when sigma is null', () => {
        const { result } = renderHook(() => useGraphExport(() => null));
        // Should not throw
        result.current.exportPNG();
    });

    it('exportPNG returns early when sigma has no canvases', () => {
        const fakeSigma: any = {
            getCanvases: () => ({}),
        };
        const { result } = renderHook(() => useGraphExport(() => fakeSigma));
        result.current.exportPNG();
        // No exception
    });

    it('exportPNG calls getSigma to fetch the renderer', () => {
        const getSigma = vi.fn(() => null);
        const { result } = renderHook(() => useGraphExport(getSigma));
        result.current.exportPNG();
        expect(getSigma).toHaveBeenCalled();
    });
});
