import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import IngestionPage from '@/app/ingestion/page';

vi.mock('next/link', () => ({
    default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

vi.mock('@tezca/ui', () => ({
    Button: ({ children, ...props }: React.PropsWithChildren) => <button {...props}>{children}</button>,
}));

vi.mock('lucide-react', () => ({
    ArrowLeft: () => <span data-testid="arrow-left" />,
}));

vi.mock('@/components/JobMonitor', () => ({
    default: () => <div data-testid="job-monitor">JobMonitor</div>,
}));

vi.mock('@/components/IngestionControl', () => ({
    default: () => <div data-testid="ingestion-control">IngestionControl</div>,
}));

describe('IngestionPage', () => {
    it('renders the page heading', () => {
        render(<IngestionPage />);
        expect(screen.getByText('Panel de Ingestión')).toBeInTheDocument();
    });

    it('renders back link to home', () => {
        render(<IngestionPage />);
        const link = screen.getByText('Volver').closest('a');
        expect(link).toHaveAttribute('href', '/');
    });

    it('renders IngestionControl component', () => {
        render(<IngestionPage />);
        expect(screen.getByTestId('ingestion-control')).toBeInTheDocument();
    });

    it('renders JobMonitor component', () => {
        render(<IngestionPage />);
        expect(screen.getByTestId('job-monitor')).toBeInTheDocument();
    });
});
