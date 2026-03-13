import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useBatchCrossRefs } from '@/hooks/useBatchCrossRefs';

// Mock the api module
vi.mock('@/lib/api', () => ({
    api: {
        getBatchArticleReferences: vi.fn(),
    },
}));

import { api } from '@/lib/api';
const mockGetBatch = vi.mocked(api.getBatchArticleReferences);

describe('useBatchCrossRefs', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns empty map when no lawId is provided', () => {
        const { result } = renderHook(() =>
            useBatchCrossRefs(undefined, ['1', '2'])
        );

        expect(result.current.refs.size).toBe(0);
        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBeNull();
        expect(mockGetBatch).not.toHaveBeenCalled();
    });

    it('returns empty map when article IDs array is empty', () => {
        const { result } = renderHook(() =>
            useBatchCrossRefs('amparo', [])
        );

        expect(result.current.refs.size).toBe(0);
        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBeNull();
        expect(mockGetBatch).not.toHaveBeenCalled();
    });

    it('fetches and returns refs correctly', async () => {
        const mockData = {
            '1': {
                outgoing: [
                    {
                        text: 'Ley de Amparo',
                        targetLawSlug: 'amparo',
                        targetArticle: '5',
                        fraction: null,
                        confidence: 0.95,
                        startPos: 10,
                        endPos: 23,
                        targetUrl: '/leyes/amparo#article-5',
                    },
                ],
                incoming: [],
            },
            '2': {
                outgoing: [],
                incoming: [
                    {
                        sourceLawSlug: 'constitucion',
                        sourceArticle: '103',
                        text: 'articulo 2',
                        confidence: 0.8,
                        sourceUrl: '/leyes/constitucion#article-103',
                    },
                ],
            },
        };
        mockGetBatch.mockResolvedValueOnce(mockData);

        const { result } = renderHook(() =>
            useBatchCrossRefs('amparo', ['1', '2'])
        );

        expect(result.current.loading).toBe(true);

        await waitFor(() => {
            expect(result.current.loading).toBe(false);
        });

        expect(result.current.refs.size).toBe(2);
        expect(result.current.refs.get('1')?.outgoing).toHaveLength(1);
        expect(result.current.refs.get('1')?.outgoing[0].text).toBe('Ley de Amparo');
        expect(result.current.refs.get('2')?.incoming).toHaveLength(1);
        expect(result.current.error).toBeNull();
    });

    it('handles API errors gracefully', async () => {
        mockGetBatch.mockRejectedValueOnce(new Error('Network error'));

        const { result } = renderHook(() =>
            useBatchCrossRefs('amparo', ['1'])
        );

        await waitFor(() => {
            expect(result.current.loading).toBe(false);
        });

        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe('Network error');
        expect(result.current.refs.size).toBe(0);
    });

    it('calls the API with correct parameters', async () => {
        mockGetBatch.mockResolvedValueOnce({});

        renderHook(() =>
            useBatchCrossRefs('constitucion', ['103', '107', '1'])
        );

        await waitFor(() => {
            expect(mockGetBatch).toHaveBeenCalledTimes(1);
        });

        expect(mockGetBatch).toHaveBeenCalledWith(
            'constitucion',
            ['103', '107', '1']
        );
    });

    it('does not refetch when article IDs have not changed', async () => {
        mockGetBatch.mockResolvedValue({});

        const { rerender } = renderHook(
            ({ lawId, ids }) => useBatchCrossRefs(lawId, ids),
            { initialProps: { lawId: 'amparo', ids: ['1', '2'] } }
        );

        await waitFor(() => {
            expect(mockGetBatch).toHaveBeenCalledTimes(1);
        });

        // Re-render with same IDs (different array reference, same content)
        rerender({ lawId: 'amparo', ids: ['1', '2'] });

        // Should still be only 1 call
        expect(mockGetBatch).toHaveBeenCalledTimes(1);
    });

    it('refetches when article IDs change', async () => {
        mockGetBatch.mockResolvedValue({});

        const { rerender } = renderHook(
            ({ lawId, ids }) => useBatchCrossRefs(lawId, ids),
            { initialProps: { lawId: 'amparo', ids: ['1', '2'] } }
        );

        await waitFor(() => {
            expect(mockGetBatch).toHaveBeenCalledTimes(1);
        });

        // Re-render with different IDs
        rerender({ lawId: 'amparo', ids: ['1', '2', '3'] });

        await waitFor(() => {
            expect(mockGetBatch).toHaveBeenCalledTimes(2);
        });
    });
});
