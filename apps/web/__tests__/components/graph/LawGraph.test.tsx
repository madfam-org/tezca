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
const mockGetGraphShowcase = vi.fn();
vi.mock('@/lib/api', async () => {
    const actual = await vi.importActual<Record<string, unknown>>('@/lib/api');
    const actualApi = actual.api as Record<string, unknown>;
    return {
        ...actual,
        api: {
            ...actualApi,
            getLawGraph: (...args: unknown[]) => mockGetLawGraph(...args),
            getGraphOverview: (...args: unknown[]) => mockGetGraphOverview(...args),
            getGraphShowcase: (...args: unknown[]) => mockGetGraphShowcase(...args),
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
        getCamera: vi.fn(() => ({ ratio: 1, animate: vi.fn(), animatedReset: vi.fn() })),
        getNodeDisplayData: vi.fn(() => ({ x: 0, y: 0 })),
        viewportToFramedGraph: vi.fn(() => ({ x: 0, y: 0 })),
        framedGraphToViewport: vi.fn(() => ({ x: 0, y: 0 })),
        getCanvases: vi.fn(() => ({})),
    })),
}));

vi.mock('graphology-layout-forceatlas2/worker', () => ({
    default: vi.fn().mockImplementation(() => ({
        start: vi.fn(),
        stop: vi.fn(),
        kill: vi.fn(),
        isRunning: vi.fn(() => false),
    })),
}));

import { LawGraphContainer } from '@/components/graph/LawGraphContainer';
import { GraphControls } from '@/components/graph/GraphControls';
import { GraphLegend } from '@/components/graph/GraphLegend';
import { GraphTooltip } from '@/components/graph/GraphTooltip';
import { GraphSearch } from '@/components/graph/GraphSearch';
import { GraphStats } from '@/components/graph/GraphStats';

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
        mockGetGraphShowcase.mockResolvedValue({ ...MOCK_GRAPH, focal_law: null });
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

    it('renders layout toggle when onToggleLayout provided', () => {
        render(
            <GraphControls
                depth={1}
                direction="both"
                minConfidence={0.5}
                isFullscreen={false}
                layoutRunning={false}
                onDepthChange={vi.fn()}
                onDirectionChange={vi.fn()}
                onConfidenceChange={vi.fn()}
                onToggleFullscreen={vi.fn()}
                onToggleLayout={vi.fn()}
            />
        );
        expect(screen.getByRole('button', { name: 'Reanudar simulación' })).toBeDefined();
    });

    it('renders export button when onExportPNG provided', () => {
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
                onExportPNG={vi.fn()}
            />
        );
        expect(screen.getByRole('button', { name: 'Exportar PNG' })).toBeDefined();
    });
});

describe('GraphLegend', () => {
    it('renders category colors by default', () => {
        render(
            <GraphLegend
                colorMode="category"
                onColorModeChange={vi.fn()}
                categories={['fiscal', 'laboral', 'penal']}
            />
        );
        expect(screen.getByText('Color por:')).toBeDefined();
        expect(screen.getByText('Fiscal')).toBeDefined();
        expect(screen.getByText('Laboral')).toBeDefined();
        expect(screen.getByText('Penal')).toBeDefined();
    });

    it('renders tier colors when in tier mode', () => {
        render(
            <GraphLegend
                colorMode="tier"
                onColorModeChange={vi.fn()}
            />
        );
        expect(screen.getByText('Federal')).toBeDefined();
        expect(screen.getByText('Estatal')).toBeDefined();
        expect(screen.getByText('Municipal')).toBeDefined();
    });

    it('shows color mode toggle buttons', () => {
        render(
            <GraphLegend
                colorMode="category"
                onColorModeChange={vi.fn()}
            />
        );
        expect(screen.getByText('Categoría')).toBeDefined();
        expect(screen.getByText('Nivel')).toBeDefined();
    });
});

describe('GraphTooltip', () => {
    it('renders nothing when node is null', () => {
        const { container } = render(<GraphTooltip node={null} position={null} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders node info with category color dot', () => {
        const node = MOCK_GRAPH.nodes[0];
        render(<GraphTooltip node={node} position={{ x: 100, y: 100 }} />);
        expect(screen.getByText('Ley de Amparo')).toBeDefined();
        expect(screen.getByText('Clic para ver')).toBeDefined();
        // Category label should appear with color dot
        expect(screen.getByText('Judicial')).toBeDefined();
    });
});

describe('GraphSearch', () => {
    const nodes = [
        { id: 'cpeum', label: 'Constitución Política' },
        { id: 'lft', label: 'Ley Federal del Trabajo' },
        { id: 'cff', label: 'Código Fiscal de la Federación' },
    ];

    it('renders search input with placeholder', () => {
        render(<GraphSearch nodes={nodes} onFocus={vi.fn()} onClear={vi.fn()} />);
        expect(screen.getByPlaceholderText('Buscar ley...')).toBeDefined();
    });
});

describe('GraphStats', () => {
    it('renders collapsible stats panel', () => {
        render(<GraphStats data={MOCK_GRAPH} />);
        expect(screen.getByText('Estadísticas')).toBeDefined();
    });
});
