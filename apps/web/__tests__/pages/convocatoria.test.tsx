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

// Import after mocks
import ConvocatoriaPage from '@/app/convocatoria/page';

async function renderPage(lang = 'es') {
    const jsx = await ConvocatoriaPage({
        searchParams: Promise.resolve({ lang }),
    });
    return render(jsx);
}

describe('ConvocatoriaPage (/convocatoria)', () => {
    it('renders page title "Convocatoria Institucional" in Spanish', async () => {
        await renderPage();
        expect(screen.getByRole('heading', { level: 1, name: 'Convocatoria Institucional' })).toBeInTheDocument();
    });

    it('renders intro text about AGPL-3.0 and mission', async () => {
        await renderPage();
        expect(screen.getByText(/Tezca es infraestructura digital pública bajo licencia AGPL-3.0/)).toBeInTheDocument();
    });

    it('renders the five partnership sections', async () => {
        await renderPage();
        expect(screen.getByText('Suprema Corte de Justicia de la Nación')).toBeInTheDocument();
        expect(screen.getByText('Congresos y Gobiernos Estatales')).toBeInTheDocument();
        expect(screen.getByText('Gobiernos Municipales')).toBeInTheDocument();
        expect(screen.getByText('Universidades y Centros de Investigación')).toBeInTheDocument();
        expect(screen.getByText('Colegios de Abogados y Barras')).toBeInTheDocument();
    });

    it('renders five partnership cards', async () => {
        await renderPage();
        const cards = screen.getAllByTestId('card');
        expect(cards).toHaveLength(5);
    });

    it('contains contact email admin@madfam.io', async () => {
        await renderPage();
        const emailLinks = screen.getAllByText(/admin@madfam.io/);
        expect(emailLinks.length).toBeGreaterThan(0);
    });

    it('renders the commitment section', async () => {
        await renderPage();
        expect(screen.getByText('Nuestro compromiso')).toBeInTheDocument();
        expect(screen.getByText(/Todo dato contribuido se publica bajo dominio público/)).toBeInTheDocument();
    });

    it('has a back link to home (/)', async () => {
        await renderPage();
        const backLink = screen.getByRole('link', { name: /Volver al inicio/ });
        expect(backLink).toHaveAttribute('href', '/');
    });

    it('contains link to /contribuir', async () => {
        await renderPage();
        const contributeLink = screen.getByRole('link', { name: /O contribuye directamente/ });
        expect(contributeLink).toHaveAttribute('href', '/contribuir');
    });

    it('renders English content when lang=en', async () => {
        await renderPage('en');
        expect(screen.getByRole('heading', { level: 1, name: 'Institutional Partnership' })).toBeInTheDocument();
        expect(screen.getByText('Supreme Court of Justice (SCJN)')).toBeInTheDocument();
        expect(screen.getByText('State Congresses and Governments')).toBeInTheDocument();
        expect(screen.getByText('Municipal Governments')).toBeInTheDocument();
        expect(screen.getByText('Universities and Research Centers')).toBeInTheDocument();
        expect(screen.getByText('Bar Associations')).toBeInTheDocument();
    });
});
