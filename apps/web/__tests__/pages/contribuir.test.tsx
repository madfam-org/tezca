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
import ContribuirPage from '@/app/contribuir/page';

async function renderPage(lang = 'es') {
    const jsx = await ContribuirPage({
        searchParams: Promise.resolve({ lang }),
    });
    return render(jsx);
}

describe('ContribuirPage (/contribuir)', () => {
    it('renders page title "Contribuir" in Spanish', async () => {
        await renderPage();
        expect(screen.getByRole('heading', { level: 1, name: 'Contribuir' })).toBeInTheDocument();
    });

    it('renders hero subtitle about completing the mirror of the law', async () => {
        await renderPage();
        expect(screen.getByText('Ayuda a completar el espejo de la ley')).toBeInTheDocument();
    });

    it('renders the data gap section', async () => {
        await renderPage();
        expect(screen.getByText('La brecha de datos')).toBeInTheDocument();
        expect(screen.getByText(/Tezca alberga más de 35,000 leyes/)).toBeInTheDocument();
    });

    it('renders two CTA cards for expert contact and data submission', async () => {
        await renderPage();
        const cards = screen.getAllByTestId('card');
        expect(cards).toHaveLength(2);

        expect(screen.getByRole('heading', { level: 3, name: 'Contacto de experto' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 3, name: 'Enviar datos' })).toBeInTheDocument();
    });

    it('has CTA card linking to /contribuir/contacto', async () => {
        await renderPage();
        const expertHeading = screen.getByRole('heading', { level: 3, name: 'Contacto de experto' });
        const expertLink = expertHeading.closest('a');
        expect(expertLink).toHaveAttribute('href', '/contribuir/contacto');
    });

    it('has CTA card linking to /contribuir/enviar-datos', async () => {
        await renderPage();
        const dataHeading = screen.getByRole('heading', { level: 3, name: 'Enviar datos' });
        const dataLink = dataHeading.closest('a');
        expect(dataLink).toHaveAttribute('href', '/contribuir/enviar-datos');
    });

    it('has a back link to home (/)', async () => {
        await renderPage();
        const backLink = screen.getByRole('link', { name: /Volver al inicio/ });
        expect(backLink).toHaveAttribute('href', '/');
    });

    it('renders open source section mentioning AGPL-3.0', async () => {
        await renderPage();
        expect(screen.getByText('Código abierto')).toBeInTheDocument();
        expect(screen.getByText(/AGPL-3.0/)).toBeInTheDocument();
    });

    it('renders GitHub repository link', async () => {
        await renderPage();
        const githubLink = screen.getByText('Ver repositorio en GitHub');
        expect(githubLink.closest('a')).toHaveAttribute('href', 'https://github.com/madfam/tezca');
    });

    it('renders English content when lang=en', async () => {
        await renderPage('en');
        expect(screen.getByRole('heading', { level: 1, name: 'Contribute' })).toBeInTheDocument();
        expect(screen.getByText('The data gap')).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 3, name: 'Expert contact' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 3, name: 'Submit data' })).toBeInTheDocument();
        expect(screen.getByText('Open source')).toBeInTheDocument();
    });
});
