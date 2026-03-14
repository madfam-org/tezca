'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Graph from 'graphology';
import Sigma from 'sigma';
import FA2Layout from 'graphology-layout-forceatlas2/worker';
import type { GraphResponse, GraphNode as APIGraphNode } from '@/lib/api';
import { GraphTooltip } from './GraphTooltip';
import {
    type ColorMode,
    FOCAL_RING_COLOR,
    getNodeColor,
    nodeSize,
    edgeSize,
    getNodeLabel,
} from './graphConstants';

interface LawGraphProps {
    data: GraphResponse;
    colorMode?: ColorMode;
    hiddenCategories?: Set<string>;
    hiddenStates?: Set<string>;
    containerClassName?: string;
    onFocusNodeRef?: (fn: ((nodeId: string) => void) | null) => void;
    onLayoutRunningChange?: (running: boolean) => void;
}

export function LawGraph({
    data,
    colorMode = 'category',
    hiddenCategories,
    hiddenStates,
    containerClassName,
    onFocusNodeRef,
    onLayoutRunningChange,
}: LawGraphProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const sigmaRef = useRef<Sigma | null>(null);
    const graphRef = useRef<Graph | null>(null);
    const layoutRef = useRef<FA2Layout | null>(null);
    const colorModeRef = useRef(colorMode);
    const router = useRouter();

    const [hoveredNode, setHoveredNode] = useState<APIGraphNode | null>(null);
    const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
    const [focusedNode, setFocusedNode] = useState<string | null>(null);

    // Keep ref in sync
    colorModeRef.current = colorMode;

    // Build graphology graph from API data
    const buildGraph = useCallback(() => {
        const graph = new Graph();

        for (const node of data.nodes) {
            graph.addNode(node.id, {
                label: node.label,
                size: nodeSize(node.ref_count),
                color: getNodeColor(colorMode, node.category, node.tier),
                tier: node.tier,
                category: node.category,
                status: node.status,
                law_type: node.law_type,
                state: node.state,
                ref_count: node.ref_count,
                is_focal: node.is_focal,
                short_name: (node as APIGraphNode & { short_name?: string }).short_name ?? null,
                x: Math.random() * 100,
                y: Math.random() * 100,
            });
        }

        for (const edge of data.edges) {
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
    }, [data, colorMode]);

    // Focus a specific node (for search)
    const focusNode = useCallback((nodeId: string) => {
        const sigma = sigmaRef.current;
        const graph = graphRef.current;
        if (!sigma || !graph || !graph.hasNode(nodeId)) return;

        setFocusedNode(nodeId);

        // Dim all non-focused nodes
        graph.forEachNode((n) => {
            graph.setNodeAttribute(n, 'color',
                n === nodeId
                    ? getNodeColor(colorModeRef.current, graph.getNodeAttribute(n, 'category'), graph.getNodeAttribute(n, 'tier'))
                    : '#e2e8f0'
            );
        });

        // Animate camera to the focused node
        const nodeData = sigma.getNodeDisplayData(nodeId);
        if (nodeData) {
            sigma.getCamera().animate(
                { x: nodeData.x, y: nodeData.y, ratio: 0.3 },
                { duration: 600 }
            );
        }
        sigma.refresh();
    }, []);

    // Clear focus
    const clearFocus = useCallback(() => {
        const graph = graphRef.current;
        const sigma = sigmaRef.current;
        if (!graph || !sigma) return;

        setFocusedNode(null);
        graph.forEachNode((n) => {
            graph.setNodeAttribute(n, 'color',
                getNodeColor(colorModeRef.current, graph.getNodeAttribute(n, 'category'), graph.getNodeAttribute(n, 'tier'))
            );
        });
        graph.forEachEdge((edge) => {
            graph.setEdgeAttribute(edge, 'hidden', false);
        });
        sigma.refresh();
    }, []);

    // Expose focusNode to parent
    useEffect(() => {
        onFocusNodeRef?.(focusNode);
        return () => onFocusNodeRef?.(null);
    }, [focusNode, onFocusNodeRef]);

    // Update colors when colorMode changes
    useEffect(() => {
        const graph = graphRef.current;
        const sigma = sigmaRef.current;
        if (!graph || !sigma) return;

        graph.forEachNode((n) => {
            graph.setNodeAttribute(n, 'color',
                getNodeColor(colorMode, graph.getNodeAttribute(n, 'category'), graph.getNodeAttribute(n, 'tier'))
            );
        });
        sigma.refresh();
    }, [colorMode]);

    // Main graph init
    useEffect(() => {
        if (!containerRef.current || data.nodes.length === 0) return;

        const graph = buildGraph();
        graphRef.current = graph;

        // Run ForceAtlas2 in a web worker for smooth layout
        let layout: FA2Layout | null = null;
        if (graph.order > 1) {
            layout = new FA2Layout(graph, {
                settings: {
                    gravity: 1,
                    scalingRatio: 2,
                    strongGravityMode: true,
                    barnesHutOptimize: graph.order > 100,
                },
            });
            layoutRef.current = layout;
            layout.start();
            onLayoutRunningChange?.(true);

            // Stop after convergence timeout
            setTimeout(() => {
                if (layout && layout.isRunning()) {
                    layout.stop();
                    onLayoutRunningChange?.(false);
                }
            }, 4000);
        }

        // Initialize Sigma
        const renderer = new Sigma(graph, containerRef.current, {
            renderEdgeLabels: false,
            labelRenderedSizeThreshold: 8,
            labelFont: 'Inter, system-ui, sans-serif',
            labelSize: 12,
            labelColor: { color: '#64748b' },
            defaultEdgeType: 'arrow',
            minEdgeThickness: 0.5,
            nodeReducer: (node, attrs) => {
                const res = { ...attrs };

                // Focal node ring
                if (graph.getNodeAttribute(node, 'is_focal')) {
                    res.borderColor = FOCAL_RING_COLOR;
                    res.borderSize = 3;
                }

                // Focused node ring (search)
                if (focusedNode && node === focusedNode) {
                    res.borderColor = FOCAL_RING_COLOR;
                    res.borderSize = 3;
                    res.zIndex = 10;
                }

                // Hide filtered nodes
                const cat = graph.getNodeAttribute(node, 'category');
                const state = graph.getNodeAttribute(node, 'state');
                if (hiddenCategories?.has(cat)) {
                    res.hidden = true;
                }
                if (hiddenStates?.size && state && hiddenStates.has(state)) {
                    res.hidden = true;
                }

                // Dynamic labels based on zoom
                const camera = sigmaRef.current?.getCamera();
                if (camera) {
                    const ratio = camera.ratio;
                    const shortName = graph.getNodeAttribute(node, 'short_name');
                    res.label = getNodeLabel(shortName, attrs.label ?? '', ratio);
                }

                return res;
            },
            edgeReducer: (edge, attrs) => {
                const res = { ...attrs };
                const source = graph.source(edge);
                const target = graph.target(edge);

                // Hide edges connected to hidden nodes
                const srcCat = graph.getNodeAttribute(source, 'category');
                const tgtCat = graph.getNodeAttribute(target, 'category');
                if (hiddenCategories?.has(srcCat) || hiddenCategories?.has(tgtCat)) {
                    res.hidden = true;
                }

                return res;
            },
        });

        sigmaRef.current = renderer;

        // ── Interactions ──────────────────────────────────────────

        renderer.on('enterNode', ({ node }) => {
            const attrs = graph.getNodeAttributes(node);
            const nodeDisplayData = renderer.getNodeDisplayData(node) as { x: number; y: number };
            const mousePos = renderer.viewportToFramedGraph(nodeDisplayData);
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
                short_name: attrs.short_name,
            } as APIGraphNode);
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
                        ? getNodeColor(colorModeRef.current, graph.getNodeAttribute(n, 'category'), graph.getNodeAttribute(n, 'tier'))
                        : '#e2e8f0'
                );
            });
            graph.forEachEdge((edge, _attrs, source, target) => {
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

            graph.forEachNode((n) => {
                graph.setNodeAttribute(n, 'color',
                    getNodeColor(colorModeRef.current, graph.getNodeAttribute(n, 'category'), graph.getNodeAttribute(n, 'tier'))
                );
            });
            graph.forEachEdge((edge) => {
                graph.setEdgeAttribute(edge, 'hidden', false);
            });
            renderer.refresh();
        });

        renderer.on('clickNode', ({ node }) => {
            router.push(`/leyes/${node}`);
        });

        // Animated entry: nodes grow from size 0 to final size
        if (graph.order > 1) {
            const finalSizes = new Map<string, number>();
            graph.forEachNode((n) => {
                finalSizes.set(n, graph.getNodeAttribute(n, 'size'));
                graph.setNodeAttribute(n, 'size', 0);
            });

            const startTime = performance.now();
            const duration = 800;

            function animate() {
                const elapsed = performance.now() - startTime;
                const progress = Math.min(1, elapsed / duration);
                // Ease-out cubic
                const eased = 1 - Math.pow(1 - progress, 3);

                graph.forEachNode((n) => {
                    const finalSize = finalSizes.get(n) ?? 6;
                    graph.setNodeAttribute(n, 'size', finalSize * eased);
                });

                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            }
            requestAnimationFrame(animate);
        }

        return () => {
            if (layout) {
                layout.kill();
                layoutRef.current = null;
            }
            renderer.kill();
            sigmaRef.current = null;
            graphRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [data, buildGraph, router]);

    // Refresh sigma when filters change
    useEffect(() => {
        sigmaRef.current?.refresh();
    }, [hiddenCategories, hiddenStates, focusedNode]);

    // Layout control methods (exposed via ref)
    const toggleLayout = useCallback(() => {
        const layout = layoutRef.current;
        if (!layout) return;
        if (layout.isRunning()) {
            layout.stop();
            onLayoutRunningChange?.(false);
        } else {
            layout.start();
            onLayoutRunningChange?.(true);
            setTimeout(() => {
                if (layout.isRunning()) {
                    layout.stop();
                    onLayoutRunningChange?.(false);
                }
            }, 4000);
        }
    }, [onLayoutRunningChange]);

    const resetCamera = useCallback(() => {
        sigmaRef.current?.getCamera().animate(
            { x: 0.5, y: 0.5, ratio: 1, angle: 0 },
            { duration: 500 }
        );
    }, []);

    // Expose layout controls to parent via custom event
    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;
        (el as HTMLDivElement & { __graphControls?: unknown }).__graphControls = {
            toggleLayout,
            resetCamera,
            clearFocus,
            getSigma: () => sigmaRef.current,
        };
    }, [toggleLayout, resetCamera, clearFocus]);

    return (
        <div className="relative w-full">
            <div
                ref={containerRef}
                className={containerClassName ?? 'w-full h-[500px] sm:h-[600px] rounded-lg border bg-background'}
                style={{ cursor: hoveredNode ? 'pointer' : 'grab' }}
            />
            <GraphTooltip node={hoveredNode} position={tooltipPos} />
        </div>
    );
}
