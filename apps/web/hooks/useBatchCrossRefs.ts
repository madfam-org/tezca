import { useState, useEffect, useRef, useMemo } from 'react';
import { api } from '@/lib/api';
import type { CrossReferenceData, IncomingCrossReference } from '@/lib/api';

export interface BatchCrossRefs {
    outgoing: CrossReferenceData[];
    incoming: IncomingCrossReference[];
}

/**
 * Fetch cross-references for a batch of articles in a single law.
 *
 * Replaces per-article N+1 fetches with one (or a few chunked) POST
 * requests to the batch endpoint.
 *
 * Returns a stable Map keyed by article ID. The map is empty while
 * loading or when no articleIds are provided.
 */
export function useBatchCrossRefs(
    lawId: string | undefined,
    articleIds: string[]
): {
    refs: Map<string, BatchCrossRefs>;
    loading: boolean;
    error: Error | null;
} {
    const [refs, setRefs] = useState<Map<string, BatchCrossRefs>>(new Map());
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    // Build a stable string key so the effect only re-runs when
    // the set of IDs actually changes, not on every render.
    const idsKey = useMemo(() => [...articleIds].sort().join(','), [articleIds]);
    const prevKey = useRef('');

    useEffect(() => {
        if (!lawId || articleIds.length === 0) {
            setRefs(new Map());
            return;
        }

        if (idsKey === prevKey.current) return;
        prevKey.current = idsKey;

        let cancelled = false;
        setLoading(true);
        setError(null);

        api.getBatchArticleReferences(lawId, articleIds)
            .then(data => {
                if (cancelled) return;
                const map = new Map<string, BatchCrossRefs>();
                for (const [id, value] of Object.entries(data)) {
                    map.set(id, {
                        outgoing: value.outgoing ?? [],
                        incoming: value.incoming ?? [],
                    });
                }
                setRefs(map);
            })
            .catch(err => {
                if (cancelled) return;
                setError(err instanceof Error ? err : new Error(String(err)));
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [lawId, idsKey]);

    return { refs, loading, error };
}
