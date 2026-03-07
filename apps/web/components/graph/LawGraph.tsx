'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Graph from 'graphology';
import Sigma from 'sigma';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import type { GraphResponse, GraphNode as APIGraphNode } from '@/lib/api';
import { GraphTooltip } from './GraphTooltip';

// Tier → color mapping using CSS variable hues
const TIER_COLORS: Record<string, string> = {
    federal: '#6366f1',    // primary/indigo
    state: '#10b981',      // chart-2/emerald
    municipal: '#f59e0b',  // chart-4/amber
};
const DEFAULT_COLOR = '#94a3b8'; // muted

const FOCAL_RING_COLOR = '#ef4444';

function getTierColor(tier: string | null): string {
    if (!tier) return DEFAULT_COLOR;
    return TIER_COLORS[tier] ?? DEFAULT_COLOR;
}

function nodeSize(refCount: number): number {
    // Logarithmic scale, min 6, max 30
    return Math.max(6, Math.min(30, 6 + Math.log2(Math.max(1, refCount)) * 3));
}

function edgeSize(weight: number): number {
    // 1-4px range
    return Math.max(1, Math.min(4, weight * 0.5));
}

interface LawGraphProps {
    data: GraphResponse;
}

export function LawGraph({ data }: LawGraphProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const sigmaRef = useRef<Sigma | null>(null);
    const graphRef = useRef<Graph | null>(null);
    const router = useRouter();

    const [hoveredNode, setHoveredNode] = useState<APIGraphNode | null>(null);
    const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

    // Build graphology graph from API data
    const buildGraph = useCallback(() => {
        const graph = new Graph();

        for (const node of data.nodes) {
            graph.addNode(node.id, {
                label: node.label,
                size: nodeSize(node.ref_count),
                color: getTierColor(node.tier),
                tier: node.tier,
                category: node.category,
                status: node.status,
                law_type: node.law_type,
                state: node.state,
                ref_count: node.ref_count,
                is_focal: node.is_focal,
                // Random initial positions — ForceAtlas2 will fix them
                x: Math.random() * 100,
                y: Math.random() * 100,
            });
        }

        for (const edge of data.edges) {
            // Skip self-loops and duplicate edges
            if (edge.source === edge.target) continue;
            if (graph.hasEdge(edge.source, edge.target)) continue;
            if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;

            graph.addEdge(edge.source, edge.target, {
                weight: edge.weight,
                size: edgeSize(edge.weight),
                color: `rgba(148, 163, 184, ${Math.min(1, 0.3 + edge.avg_confidence * 0.7)})`,
            });
        }

        return graph;
    }, [data]);

    useEffect(() => {
        if (!containerRef.current || data.nodes.length === 0) return;

        const graph = buildGraph();
        graphRef.current = graph;

        // Run ForceAtlas2 layout synchronously (small graphs)
        if (graph.order > 1) {
            forceAtlas2.assign(graph, {
                iterations: 100,
                settings: {
                    gravity: 1,
                    scalingRatio: 2,
                    strongGravityMode: true,
                    barnesHutOptimize: graph.order > 100,
                },
            });
        }

        // Initialize Sigma
        const renderer = new Sigma(graph, containerRef.current, {
            renderEdgeLabels: false,
            labelRenderedSizeThreshold: 8,
            labelFont: 'Inter, system-ui, sans-serif',
            labelSize: 12,
            labelColor: { color: '#64748b' },
            defaultEdgeType: 'line',
            minEdgeThickness: 0.5,
            // Node reducer to highlight focal node and dim on hover
            nodeReducer: (node, attrs) => {
                const res = { ...attrs };

                // Focal node ring
                if (graph.getNodeAttribute(node, 'is_focal')) {
                    res.borderColor = FOCAL_RING_COLOR;
                    res.borderSize = 3;
                }

                return res;
            },
        });

        sigmaRef.current = renderer;

        // ── Interactions ──────────────────────────────────────────

        // Hover: show tooltip
        renderer.on('enterNode', ({ node }) => {
            const attrs = graph.getNodeAttributes(node);
            const mousePos = renderer.viewportToFramedGraph(
                renderer.getNodeDisplayData(node) as { x: number; y: number }
            );
            const domPos = renderer.framedGraphToViewport(mousePos);
            const container = containerRef.current?.getBoundingClientRect();

            setHoveredNode({
                id: node,
                label: attrs.label,
                tier: attrs.tier,
                category: attrs.category,
                status: attrs.status,
                law_type: attrs.law_type,
                state: attrs.state,
                ref_count: attrs.ref_count,
                is_focal: attrs.is_focal,
            });
            setTooltipPos({
                x: (container?.left ?? 0) + domPos.x,
                y: (container?.top ?? 0) + domPos.y,
            });

            // Dim non-neighbors
            const neighbors = new Set(graph.neighbors(node));
            neighbors.add(node);
            graph.forEachNode((n) => {
                graph.setNodeAttribute(
                    n,
                    'color',
                    neighbors.has(n)
                        ? getTierColor(graph.getNodeAttribute(n, 'tier'))
                        : '#e2e8f0'
                );
            });
            graph.forEachEdge((edge, attrs, source, target) => {
                graph.setEdgeAttribute(
                    edge,
                    'hidden',
                    source !== node && target !== node
                );
            });
            renderer.refresh();
        });

        renderer.on('leaveNode', () => {
            setHoveredNode(null);
            setTooltipPos(null);

            // Restore all colors
            graph.forEachNode((n) => {
                graph.setNodeAttribute(n, 'color', getTierColor(graph.getNodeAttribute(n, 'tier')));
            });
            graph.forEachEdge((edge) => {
                graph.setEdgeAttribute(edge, 'hidden', false);
            });
            renderer.refresh();
        });

        // Click: navigate to law
        renderer.on('clickNode', ({ node }) => {
            router.push(`/leyes/${node}`);
        });

        return () => {
            renderer.kill();
            sigmaRef.current = null;
            graphRef.current = null;
        };
    }, [data, buildGraph, router]);

    return (
        <div className="relative w-full">
            <div
                ref={containerRef}
                className="w-full h-[400px] rounded-lg border bg-background"
                style={{ cursor: hoveredNode ? 'pointer' : 'grab' }}
            />
            <GraphTooltip node={hoveredNode} position={tooltipPos} />
        </div>
    );
}
