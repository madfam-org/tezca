import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div data-testid="card" className={className}>{children}</div>
    ),
    CardContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <div className={className}>{children}</div>
    ),
}));

// Mock LanguageToggle
vi.mock('@/components/LanguageToggle', () => ({
    LanguageToggle: () => <div data-testid="language-toggle" />,
}));

// Mock CoverageDashboard (client component)
vi.mock('@/components/coverage/CoverageDashboard', () => ({
    CoverageDashboard: () => <div data-testid="coverage-dashboard">Dashboard</div>,
}));

// Import after mocks
import CoberturaPage from '@/app/cobertura/page';

async function renderPage(lang = 'es') {
    const jsx = await CoberturaPage({
        searchParams: Promise.resolve({ lang }),
    });
    return render(jsx);
}

describe('CoberturaPage (/cobertura)', () => {
    it('renders page title "Cobertura de Datos" in Spanish', async () => {
        await renderPage();
        expect(screen.getByRole('heading', { level: 1, name: 'Cobertura de Datos' })).toBeInTheDocument();
    });

    it('renders intro text about coverage progress', async () => {
        await renderPage();
        expect(screen.getByText(/Tezca aspira a capturar la totalidad del marco jurídico mexicano/)).toBeInTheDocument();
    });

    it('renders the CoverageDashboard component', async () => {
        await renderPage();
        expect(screen.getByTestId('coverage-dashboard')).toBeInTheDocument();
    });

    it('renders methodology section', async () => {
        await renderPage();
        expect(screen.getByText('Metodología')).toBeInTheDocument();
    });

    it('renders "Cómo puedes ayudar" section', async () => {
        await renderPage();
        expect(screen.getByText('¿Cómo puedes ayudar?')).toBeInTheDocument();
    });

    it('contains link to /contribuir', async () => {
        await renderPage();
        const contribuirLink = screen.getByRole('link', { name: 'Contribuir datos' });
        expect(contribuirLink).toHaveAttribute('href', '/contribuir');
    });

    it('contains link to /convocatoria', async () => {
        await renderPage();
        const partnershipLink = screen.getByRole('link', { name: 'Convocatoria institucional' });
        expect(partnershipLink).toHaveAttribute('href', '/convocatoria');
    });

    it('has a back link to home (/)', async () => {
        await renderPage();
        const backLink = screen.getByRole('link', { name: /Volver al inicio/ });
        expect(backLink).toHaveAttribute('href', '/');
    });

    it('renders data sources section with source cards', async () => {
        await renderPage();
        expect(screen.getByText('Fuentes de datos')).toBeInTheDocument();
        expect(screen.getByText('Cámara de Diputados')).toBeInTheDocument();
        expect(screen.getByText('CONAMER')).toBeInTheDocument();
    });

    it('renders English content when lang=en', async () => {
        await renderPage('en');
        expect(screen.getByRole('heading', { level: 1, name: 'Data Coverage' })).toBeInTheDocument();
        expect(screen.getByText('How you can help')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Contribute data' })).toHaveAttribute('href', '/contribuir');
    });
});
