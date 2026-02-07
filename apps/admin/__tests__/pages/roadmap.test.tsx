import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RoadmapPage from '@/app/roadmap/page';

vi.mock('next/link', () => ({
    default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

vi.mock('@tezca/ui', () => ({
    Button: ({ children, onClick, disabled, ...props }: React.PropsWithChildren<{ onClick?: () => void; disabled?: boolean }>) => (
        <button onClick={onClick} disabled={disabled} {...props}>{children}</button>
    ),
    Card: ({ children, ...props }: React.PropsWithChildren) => <div data-testid="card" {...props}>{children}</div>,
    CardHeader: ({ children, onClick, ...props }: React.PropsWithChildren<{ onClick?: () => void }>) => (
        <div onClick={onClick} {...props}>{children}</div>
    ),
    CardTitle: ({ children, ...props }: React.PropsWithChildren) => <h3 {...props}>{children}</h3>,
    CardContent: ({ children, ...props }: React.PropsWithChildren) => <div {...props}>{children}</div>,
    Badge: ({ children, ...props }: React.PropsWithChildren) => <span data-testid="badge" {...props}>{children}</span>,
}));

vi.mock('lucide-react', () => ({
    ArrowLeft: () => <span data-testid="arrow-left" />,
    RefreshCw: () => <span data-testid="refresh" />,
    Rocket: () => <span data-testid="rocket" />,
    ChevronDown: () => <span data-testid="chevron-down" />,
    ChevronRight: () => <span data-testid="chevron-right" />,
}));

const mockRoadmapData = {
    summary: {
        total_items: 15,
        completed: 5,
        in_progress: 3,
        total_estimated_laws: 50000,
    },
    phases: [
        {
            phase: 1,
            label: 'Core Federal',
            items: [
                {
                    id: 1,
                    title: 'Federal laws',
                    description: 'All federal laws',
                    category: 'scraper',
                    status: 'completed',
                    estimated_laws: 333,
                    estimated_effort: '2 weeks',
                    priority: 1,
                    progress_pct: 100,
                    notes: null,
                    started_at: '2026-01-01T00:00:00Z',
                    completed_at: '2026-01-15T00:00:00Z',
                },
            ],
            total: 3,
            completed: 2,
            in_progress: 1,
            estimated_laws: 1000,
        },
    ],
};

vi.mock('@/lib/api', () => ({
    api: {
        getRoadmap: vi.fn(),
        updateRoadmapItem: vi.fn(),
    },
}));

describe('RoadmapPage', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('renders page heading', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockReturnValue(new Promise(() => {}));

        render(<RoadmapPage />);
        expect(screen.getByText('Hoja de Ruta de Expansión')).toBeInTheDocument();
    });

    it('renders back link to home', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockReturnValue(new Promise(() => {}));

        render(<RoadmapPage />);
        const link = screen.getByText('Volver').closest('a');
        expect(link).toHaveAttribute('href', '/');
    });

    it('shows loading skeleton initially', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockReturnValue(new Promise(() => {}));

        const { container } = render(<RoadmapPage />);
        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('renders summary cards after loading', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockResolvedValue(mockRoadmapData);

        render(<RoadmapPage />);

        await waitFor(() => {
            expect(screen.getByText('15')).toBeInTheDocument();
        });

        expect(screen.getByText('Total')).toBeInTheDocument();
        expect(screen.getByText('5')).toBeInTheDocument();
        expect(screen.getByText('Completados')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByText('En Progreso')).toBeInTheDocument();
        expect(screen.getByText('50,000')).toBeInTheDocument();
        expect(screen.getByText('Leyes Estimadas')).toBeInTheDocument();
    });

    it('renders phase sections with items', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockResolvedValue(mockRoadmapData);

        render(<RoadmapPage />);

        await waitFor(() => {
            expect(screen.getByText(/Fase 1: Core Federal/)).toBeInTheDocument();
        });

        expect(screen.getByText('Federal laws')).toBeInTheDocument();
    });

    it('shows error state with retry button', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockRejectedValue(new Error('Network error'));

        render(<RoadmapPage />);

        await waitFor(() => {
            expect(screen.getByText('Network error')).toBeInTheDocument();
        });

        expect(screen.getByText('Reintentar')).toBeInTheDocument();
    });

    it('renders refresh button', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getRoadmap).mockReturnValue(new Promise(() => {}));

        render(<RoadmapPage />);
        expect(screen.getByText('Actualizar')).toBeInTheDocument();
    });
});
