import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { GraphResponse } from '@/lib/api';

// Mock next/navigation
vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
    usePathname: vi.fn(() => '/grafo'),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock the api module
const mockGetLawGraph = vi.fn();
const mockGetGraphOverview = vi.fn();
vi.mock('@/lib/api', async () => {
    const actual = await vi.importActual<Record<string, unknown>>('@/lib/api');
    const actualApi = actual.api as Record<string, unknown>;
    return {
        ...actual,
        api: {
            ...actualApi,
            getLawGraph: (...args: unknown[]) => mockGetLawGraph(...args),
            getGraphOverview: (...args: unknown[]) => mockGetGraphOverview(...args),
        },
    };
});

// Mock sigma (WebGL not available in jsdom)
vi.mock('sigma', () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
        off: vi.fn(),
        kill: vi.fn(),
        refresh: vi.fn(),
        getNodeDisplayData: vi.fn(() => ({ x: 0, y: 0 })),
        viewportToFramedGraph: vi.fn(() => ({ x: 0, y: 0 })),
        framedGraphToViewport: vi.fn(() => ({ x: 0, y: 0 })),
    })),
}));

vi.mock('graphology-layout-forceatlas2', () => ({
    default: { assign: vi.fn() },
    assign: vi.fn(),
}));

import { LawGraphContainer } from '@/components/graph/LawGraphContainer';
import { GraphControls } from '@/components/graph/GraphControls';
import { GraphLegend } from '@/components/graph/GraphLegend';
import { GraphTooltip } from '@/components/graph/GraphTooltip';

const MOCK_GRAPH: GraphResponse = {
    focal_law: 'amparo',
    nodes: [
        { id: 'amparo', label: 'Ley de Amparo', tier: 'federal', category: 'judicial', status: 'vigente', law_type: 'legislative', state: null, ref_count: 45, is_focal: true },
        { id: 'cpeum', label: 'Constitución', tier: 'federal', category: 'constitutional', status: 'vigente', law_type: 'legislative', state: null, ref_count: 120, is_focal: false },
    ],
    edges: [
        { id: 'amparo->cpeum', source: 'amparo', target: 'cpeum', weight: 23, avg_confidence: 0.87 },
    ],
    meta: { total_nodes: 2, total_edges: 1, depth_reached: 1, truncated: false },
};

describe('LawGraphContainer', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetLawGraph.mockResolvedValue(MOCK_GRAPH);
        mockGetGraphOverview.mockResolvedValue({ ...MOCK_GRAPH, focal_law: null });
    });

    it('shows loading state initially', () => {
        // Never-resolving promise to keep loading state
        mockGetLawGraph.mockReturnValue(new Promise(() => {}));
        render(<LawGraphContainer lawId="amparo" />);
        expect(screen.getByText('Cargando grafo...')).toBeDefined();
    });

    it('shows empty state when no nodes', async () => {
        mockGetLawGraph.mockResolvedValue({
            ...MOCK_GRAPH,
            nodes: [],
            edges: [],
            meta: { total_nodes: 0, total_edges: 0, depth_reached: 0, truncated: false },
        });
        render(<LawGraphContainer lawId="empty-law" />);
        // Wait for loading to finish
        const empty = await screen.findByText('No hay referencias suficientes para visualizar');
        expect(empty).toBeDefined();
    });

    it('renders graph section title for law', () => {
        mockGetLawGraph.mockReturnValue(new Promise(() => {}));
        render(<LawGraphContainer lawId="amparo" />);
        expect(screen.getByText('Grafo de referencias')).toBeDefined();
    });

    it('renders overview title without lawId', () => {
        mockGetGraphOverview.mockReturnValue(new Promise(() => {}));
        render(<LawGraphContainer />);
        expect(screen.getByText('Red de leyes')).toBeDefined();
    });
});

describe('GraphControls', () => {
    it('renders depth and direction selectors', () => {
        render(
            <GraphControls
                depth={1}
                direction="both"
                minConfidence={0.5}
                isFullscreen={false}
                onDepthChange={vi.fn()}
                onDirectionChange={vi.fn()}
                onConfidenceChange={vi.fn()}
                onToggleFullscreen={vi.fn()}
            />
        );
        expect(screen.getByText('Profundidad:')).toBeDefined();
        expect(screen.getByText('Dirección:')).toBeDefined();
    });

    it('calls callbacks on depth change', () => {
        const onDepthChange = vi.fn();
        render(
            <GraphControls
                depth={1}
                direction="both"
                minConfidence={0.5}
                isFullscreen={false}
                onDepthChange={onDepthChange}
                onDirectionChange={vi.fn()}
                onConfidenceChange={vi.fn()}
                onToggleFullscreen={vi.fn()}
            />
        );
        const select = screen.getAllByRole('combobox')[0];
        select.dispatchEvent(new Event('change', { bubbles: true }));
    });
});

describe('GraphLegend', () => {
    it('renders tier color labels', () => {
        render(<GraphLegend />);
        expect(screen.getByText('Leyenda:')).toBeDefined();
        expect(screen.getByText('Federal')).toBeDefined();
        expect(screen.getByText('Estatal')).toBeDefined();
        expect(screen.getByText('Municipal')).toBeDefined();
    });
});

describe('GraphTooltip', () => {
    it('renders nothing when node is null', () => {
        const { container } = render(<GraphTooltip node={null} position={null} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders node info when provided', () => {
        const node = MOCK_GRAPH.nodes[0];
        render(<GraphTooltip node={node} position={{ x: 100, y: 100 }} />);
        expect(screen.getByText('Ley de Amparo')).toBeDefined();
        expect(screen.getByText('Clic para ver')).toBeDefined();
    });
});
