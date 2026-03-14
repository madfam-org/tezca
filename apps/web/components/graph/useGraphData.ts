'use client';

import { useState, useEffect, useRef } from 'react';
import { api, type GraphResponse } from '@/lib/api';

interface UseGraphDataOptions {
    lawId?: string;
    depth?: number;
    min_confidence?: number;
    max_nodes?: number;
    direction?: string;
    // Overview mode options
    tier?: string;
    category?: string;
    min_weight?: number;
    // Showcase fallback
    showcase?: boolean;
}

export function useGraphData(opts: UseGraphDataOptions) {
    const [graph, setGraph] = useState<GraphResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isShowcase, setIsShowcase] = useState(false);
    const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);

        debounceRef.current = setTimeout(async () => {
            try {
                setLoading(true);
                setError(null);

                let data: GraphResponse;

                if (opts.lawId) {
                    data = await api.getLawGraph(opts.lawId, {
                        depth: opts.depth,
                        min_confidence: opts.min_confidence,
                        max_nodes: opts.max_nodes,
                        direction: opts.direction,
                    });
                } else if (opts.showcase) {
                    data = await api.getGraphShowcase();
                    setIsShowcase(true);
                } else {
                    try {
                        data = await api.getGraphOverview({
                            tier: opts.tier,
                            category: opts.category,
                            min_weight: opts.min_weight,
                            max_nodes: opts.max_nodes,
                        });
                        setIsShowcase(false);
                    } catch (overviewErr: unknown) {
                        // Fallback to showcase for unauthenticated/unauthorized users (401/403)
                        const status = (overviewErr as { status?: number })?.status;
                        if (status === 401 || status === 403) {
                            data = await api.getGraphShowcase();
                            setIsShowcase(true);
                        } else {
                            throw overviewErr;
                        }
                    }
                }

                setGraph(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load graph');
            } finally {
                setLoading(false);
            }
        }, 300);

        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, [opts.lawId, opts.depth, opts.min_confidence, opts.max_nodes, opts.direction, opts.tier, opts.category, opts.min_weight, opts.showcase]);

    return { graph, loading, error, isShowcase };
}
