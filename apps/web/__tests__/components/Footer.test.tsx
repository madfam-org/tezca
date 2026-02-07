import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Footer } from '@/components/Footer';
import { LanguageProvider } from '@/components/providers/LanguageContext';

function renderFooter() {
  return render(
    <LanguageProvider>
      <Footer />
    </LanguageProvider>
  );
}

describe('Footer', () => {
  it('renders copyright text in Spanish by default', () => {
    renderFooter();
    expect(screen.getByText(/Todos los derechos reservados/)).toBeInTheDocument();
  });

  it('renders explore nav links with correct hrefs', () => {
    renderFooter();
    const homeLink = screen.getByRole('link', { name: 'Inicio' });
    expect(homeLink).toHaveAttribute('href', '/');

    const searchLink = screen.getByRole('link', { name: 'Buscar Leyes' });
    expect(searchLink).toHaveAttribute('href', '/busqueda');

    const catalogLink = screen.getByRole('link', { name: 'Catálogo' });
    expect(catalogLink).toHaveAttribute('href', '/leyes');

    const aboutLink = screen.getByRole('link', { name: 'Acerca de' });
    expect(aboutLink).toHaveAttribute('href', '/acerca-de');
  });

  it('renders legal links with correct hrefs', () => {
    renderFooter();
    const termsLink = screen.getByRole('link', { name: 'Términos y Condiciones' });
    expect(termsLink).toHaveAttribute('href', '/terminos');

    const noticeLink = screen.getByRole('link', { name: 'Aviso Legal' });
    expect(noticeLink).toHaveAttribute('href', '/aviso-legal');

    const privacyLink = screen.getByRole('link', { name: 'Privacidad' });
    expect(privacyLink).toHaveAttribute('href', '/privacidad');
  });

  it('renders external links with target="_blank" and rel="noopener noreferrer"', () => {
    renderFooter();
    const dofLinks = screen.getAllByRole('link', { name: /DOF/ });
    // At least the official sources column DOF link
    const externalDof = dofLinks.find(link => link.getAttribute('href') === 'https://www.dof.gob.mx');
    expect(externalDof).toBeDefined();
    expect(externalDof).toHaveAttribute('target', '_blank');
    expect(externalDof).toHaveAttribute('rel', 'noopener noreferrer');

    const ojnLink = screen.getByRole('link', { name: /OJN/ });
    expect(ojnLink).toHaveAttribute('target', '_blank');
    expect(ojnLink).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders disclaimer bar text', () => {
    renderFooter();
    expect(
      screen.getByText(/proyecto informativo independiente/)
    ).toBeInTheDocument();
  });
});
