import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AcercaDePage from '@/app/acerca-de/page';
import { LanguageProvider } from '@/components/providers/LanguageContext';

async function renderPage(lang = 'es') {
  const jsx = await AcercaDePage({
    searchParams: Promise.resolve({ lang }),
  });
  return render(<LanguageProvider>{jsx}</LanguageProvider>);
}

describe('AcercaDe (Manifesto Page)', () => {
  it('renders "Tezca" title in hero section', async () => {
    await renderPage();
    expect(screen.getByRole('heading', { level: 1, name: 'Tezca' })).toBeInTheDocument();
  });

  it('renders subtitle "El Espejo de la Ley" in Spanish by default', async () => {
    await renderPage();
    expect(screen.getByText('El Espejo de la Ley')).toBeInTheDocument();
  });

  it('renders all five manifesto sections with Roman numerals', async () => {
    await renderPage();
    const numerals = ['I', 'II', 'III', 'IV', 'V'];
    numerals.forEach((numeral) => {
      expect(screen.getByText(numeral)).toBeInTheDocument();
    });
  });

  it('renders all five section titles in Spanish by default', async () => {
    await renderPage();
    expect(screen.getByText('La Sombra')).toBeInTheDocument();
    expect(screen.getByText('El Tezcatl')).toBeInTheDocument();
    expect(screen.getByText('La Transformación')).toBeInTheDocument();
    expect(screen.getByText('Infraestructura, no Especulación')).toBeInTheDocument();
    expect(screen.getByText('El Futuro')).toBeInTheDocument();
  });

  it('renders closing CTA "Bienvenido a Tezca"', async () => {
    await renderPage();
    expect(screen.getByText('Bienvenido a Tezca')).toBeInTheDocument();
  });

  it('renders English content when lang=en', async () => {
    await renderPage('en');
    expect(screen.getByText('The Mirror of the Law')).toBeInTheDocument();
    expect(screen.getByText('The Shadow')).toBeInTheDocument();
    expect(screen.getByText('The Tezcatl')).toBeInTheDocument();
    expect(screen.getByText('The Transformation')).toBeInTheDocument();
    expect(screen.getByText('Infrastructure, not Speculation')).toBeInTheDocument();
    expect(screen.getByText('The Future')).toBeInTheDocument();
    expect(screen.getByText('Welcome to Tezca')).toBeInTheDocument();
  });

  it('has a link back to home', async () => {
    await renderPage();
    const backLink = screen.getByRole('link', { name: /Volver al inicio|Back to home/ });
    expect(backLink).toHaveAttribute('href', '/');
  });
});
