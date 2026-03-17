import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MetricsPage from '@/app/metrics/page';

vi.mock('next/link', () => ({
    default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

vi.mock('@tezca/ui', () => ({
    Card: ({ children, ...props }: React.PropsWithChildren) => <div {...props}>{children}</div>,
    CardHeader: ({ children, ...props }: React.PropsWithChildren) => <div {...props}>{children}</div>,
    CardTitle: ({ children, ...props }: React.PropsWithChildren) => <h3 {...props}>{children}</h3>,
    CardContent: ({ children, ...props }: React.PropsWithChildren) => <div {...props}>{children}</div>,
    Button: ({ children, disabled, onClick, asChild, ...props }: React.PropsWithChildren<{ disabled?: boolean; onClick?: () => void; asChild?: boolean; variant?: string; size?: string }>) => {
        if (asChild) return <>{children}</>;
        return <button disabled={disabled} onClick={onClick} {...props}>{children}</button>;
    },
}));

const mockMetrics = {
    total_laws: 1500,
    counts: { federal: 300, state: 900, municipal: 300 },
    top_categories: [
        { category: 'constitucional', count: 200 },
        { category: 'fiscal', count: 150 },
    ],
    quality_distribution: null,
    last_updated: '2026-02-01T12:00:00Z',
};

const mockGetMetrics = vi.fn();

vi.mock('@/lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@/lib/api')>();
    return {
        ...actual,
        api: {
            getMetrics: (...args: unknown[]) => mockGetMetrics(...args),
        },
    };
});

describe('Metrics page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows loading skeleton initially', () => {
        mockGetMetrics.mockReturnValue(new Promise(() => {}));
        render(<MetricsPage />);
        expect(screen.getByText('Métricas del Sistema')).toBeInTheDocument();
        expect(screen.queryByText('Total de Leyes')).not.toBeInTheDocument();
    });

    it('renders metric cards on success', async () => {
        mockGetMetrics.mockResolvedValue(mockMetrics);
        render(<MetricsPage />);

        await waitFor(() => {
            expect(screen.getByText('Total de Leyes')).toBeInTheDocument();
        });
        expect(screen.getByText('1,500')).toBeInTheDocument();
        expect(screen.getByText('Federales')).toBeInTheDocument();
        expect(screen.getByText('Estatales')).toBeInTheDocument();
        expect(screen.getByText('Municipales')).toBeInTheDocument();
    });

    it('renders categories with progress bars', async () => {
        mockGetMetrics.mockResolvedValue(mockMetrics);
        render(<MetricsPage />);

        await waitFor(() => {
            expect(screen.getByText('Categorías Principales')).toBeInTheDocument();
        });
        expect(screen.getByText('constitucional')).toBeInTheDocument();
        expect(screen.getByText('fiscal')).toBeInTheDocument();
    });

    it('shows quality distribution placeholder when null', async () => {
        mockGetMetrics.mockResolvedValue(mockMetrics);
        render(<MetricsPage />);

        await waitFor(() => {
            expect(screen.getByText(/distribución de calidad por ley aún no está disponible/i)).toBeInTheDocument();
        });
    });

    it('displays error message on fetch failure', async () => {
        mockGetMetrics.mockRejectedValue(new Error('API unavailable'));
        render(<MetricsPage />);

        await waitFor(() => {
            expect(screen.getByText('API unavailable')).toBeInTheDocument();
        });
    });

    it('refresh button re-fetches metrics', async () => {
        mockGetMetrics.mockResolvedValue(mockMetrics);
        const user = userEvent.setup();
        render(<MetricsPage />);

        await waitFor(() => {
            expect(screen.getByText('Total de Leyes')).toBeInTheDocument();
        });

        const refreshBtn = screen.getByRole('button', { name: /actualizar/i });
        await user.click(refreshBtn);

        expect(mockGetMetrics).toHaveBeenCalledTimes(2);
    });

    it('renders back link to home', async () => {
        mockGetMetrics.mockResolvedValue(mockMetrics);
        render(<MetricsPage />);
        await waitFor(() => {
            expect(screen.getByText('Total de Leyes')).toBeInTheDocument();
        });
        const backLink = screen.getByRole('link', { name: /volver/i });
        expect(backLink).toHaveAttribute('href', '/');
    });
});
