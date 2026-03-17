import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/settings/page';

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
    Badge: ({ children, variant, ...props }: React.PropsWithChildren<{ variant?: string }>) => (
        <span data-variant={variant} {...props}>{children}</span>
    ),
    Button: ({ children, disabled, onClick, asChild, ...props }: React.PropsWithChildren<{ disabled?: boolean; onClick?: () => void; asChild?: boolean; variant?: string; size?: string }>) => {
        if (asChild) return <>{children}</>;
        return <button disabled={disabled} onClick={onClick} {...props}>{children}</button>;
    },
}));

const mockConfig = {
    environment: {
        debug: false,
        allowed_hosts: ['localhost', '*.leyes.mx'],
        language: 'es-mx',
        timezone: 'America/Mexico_City',
    },
    database: { engine: 'postgresql', status: 'connected', name: 'leyes_mx' },
    elasticsearch: { host: 'http://localhost:9200', status: 'connected' },
    data: { total_laws: 1500, total_versions: 3200, latest_publication: '2026-01-15' },
};

const mockHealth = {
    status: 'healthy',
    database: 'ok',
    timestamp: '2026-02-01T12:00:00Z',
};

const mockGetConfig = vi.fn();
const mockGetHealth = vi.fn();

vi.mock('@/lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@/lib/api')>();
    return {
        ...actual,
        api: {
            getConfig: (...args: unknown[]) => mockGetConfig(...args),
            getHealth: (...args: unknown[]) => mockGetHealth(...args),
        },
    };
});

describe('Settings page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows loading skeleton initially', () => {
        mockGetConfig.mockReturnValue(new Promise(() => {}));
        mockGetHealth.mockReturnValue(new Promise(() => {}));
        render(<SettingsPage />);
        expect(screen.getByText('Configuración del Sistema')).toBeInTheDocument();
    });

    it('renders all config cards on success', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue(mockHealth);
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Estado del Servicio')).toBeInTheDocument();
        });
        expect(screen.getByText('Base de Datos')).toBeInTheDocument();
        expect(screen.getByText('Elasticsearch')).toBeInTheDocument();
        expect(screen.getByText('Datos')).toBeInTheDocument();
        expect(screen.getByText('Entorno')).toBeInTheDocument();
    });

    it('shows healthy badge when status is healthy', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue(mockHealth);
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Saludable')).toBeInTheDocument();
        });
    });

    it('shows error badge when health status is not healthy', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue({ ...mockHealth, status: 'unhealthy' });
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Error')).toBeInTheDocument();
        });
    });

    it('shows debug badge as Inactivo when debug is false', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue(mockHealth);
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Inactivo')).toBeInTheDocument();
        });
    });

    it('shows debug badge as Activo when debug is true', async () => {
        mockGetConfig.mockResolvedValue({ ...mockConfig, environment: { ...mockConfig.environment, debug: true } });
        mockGetHealth.mockResolvedValue(mockHealth);
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Activo')).toBeInTheDocument();
        });
    });

    it('renders database connection status', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue(mockHealth);
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Conectada')).toBeInTheDocument();
        });
    });

    it('renders data summary with formatted numbers', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue(mockHealth);
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('1,500')).toBeInTheDocument();
        });
        expect(screen.getByText('3,200')).toBeInTheDocument();
    });

    it('displays error on fetch failure', async () => {
        mockGetConfig.mockRejectedValue(new Error('Connection refused'));
        mockGetHealth.mockRejectedValue(new Error('Connection refused'));
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Connection refused')).toBeInTheDocument();
        });
    });

    it('refresh button re-fetches both config and health', async () => {
        mockGetConfig.mockResolvedValue(mockConfig);
        mockGetHealth.mockResolvedValue(mockHealth);
        const user = userEvent.setup();
        render(<SettingsPage />);

        await waitFor(() => {
            expect(screen.getByText('Estado del Servicio')).toBeInTheDocument();
        });

        const refreshBtn = screen.getByRole('button', { name: /actualizar/i });
        await user.click(refreshBtn);

        expect(mockGetConfig).toHaveBeenCalledTimes(2);
        expect(mockGetHealth).toHaveBeenCalledTimes(2);
    });
});
