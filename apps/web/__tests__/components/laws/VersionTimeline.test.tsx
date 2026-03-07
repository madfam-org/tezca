import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { VersionTimeline } from '@/components/laws/VersionTimeline';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { makeVersions } from '../../fixtures/mockFactories';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe('VersionTimeline', () => {
    it('renders nothing with 0 versions', () => {
        const { container } = renderWithLang(<VersionTimeline versions={[]} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders nothing with 1 version', () => {
        const versions = makeVersions(1);
        const { container } = renderWithLang(<VersionTimeline versions={versions} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders timeline header with version count', () => {
        const versions = makeVersions(5);
        renderWithLang(<VersionTimeline versions={versions} />);

        expect(screen.getByText('Historial de Versiones')).toBeInTheDocument();
        expect(screen.getByText('5 versiones publicadas')).toBeInTheDocument();
    });

    it('formats dates with locale', async () => {
        const user = userEvent.setup();
        const versions = makeVersions(2);
        renderWithLang(<VersionTimeline versions={versions} />);

        // Expand the timeline
        await user.click(screen.getByRole('button', { expanded: false }));

        // The first version has publication_date '2024-06-06'
        // toLocaleDateString with es-MX gives something like "6 de junio de 2024"
        // Multiple elements may match (publication_date + valid_from both in June)
        const juneElements = screen.getAllByText(/junio/i);
        expect(juneElements.length).toBeGreaterThanOrEqual(1);
    });

    it('handles null publication_date', async () => {
        const user = userEvent.setup();
        const versions = [
            { publication_date: null, dof_url: null, change_summary: null },
            { publication_date: '2023-01-01', dof_url: null, change_summary: null },
        ];
        renderWithLang(<VersionTimeline versions={versions} />);

        await user.click(screen.getByRole('button', { expanded: false }));

        expect(screen.getByText('Fecha desconocida')).toBeInTheDocument();
    });

    it('first version shows "Vigente" badge', async () => {
        const user = userEvent.setup();
        const versions = makeVersions(3);
        renderWithLang(<VersionTimeline versions={versions} />);

        await user.click(screen.getByRole('button', { expanded: false }));

        expect(screen.getByText('Vigente')).toBeInTheDocument();
    });

    it('subsequent versions show "Superada" badge', async () => {
        const user = userEvent.setup();
        const versions = makeVersions(3);
        renderWithLang(<VersionTimeline versions={versions} />);

        await user.click(screen.getByRole('button', { expanded: false }));

        const superseded = screen.getAllByText('Superada');
        expect(superseded).toHaveLength(2);
    });

    it('renders change_summary text', async () => {
        const user = userEvent.setup();
        const versions = [
            { publication_date: '2024-06-06', change_summary: 'Reforma educativa integral', dof_url: null },
            { publication_date: '2023-01-01', change_summary: 'Reforma fiscal', dof_url: null },
        ];
        renderWithLang(<VersionTimeline versions={versions} />);

        await user.click(screen.getByRole('button', { expanded: false }));

        expect(screen.getByText('Reforma educativa integral')).toBeInTheDocument();
        expect(screen.getByText('Reforma fiscal')).toBeInTheDocument();
    });

    it('renders DOF external link', async () => {
        const user = userEvent.setup();
        const versions = [
            { publication_date: '2024-06-06', dof_url: 'https://dof.gob.mx/nota/1234', change_summary: null },
            { publication_date: '2023-01-01', dof_url: null, change_summary: null },
        ];
        renderWithLang(<VersionTimeline versions={versions} />);

        await user.click(screen.getByRole('button', { expanded: false }));

        const dofLink = screen.getByText('Ver en DOF');
        expect(dofLink.closest('a')).toHaveAttribute('href', 'https://dof.gob.mx/nota/1234');
        expect(dofLink.closest('a')).toHaveAttribute('target', '_blank');
    });

    it('handles many versions (20+)', async () => {
        const user = userEvent.setup();
        const versions = makeVersions(25);
        renderWithLang(<VersionTimeline versions={versions} />);

        expect(screen.getByText('25 versiones publicadas')).toBeInTheDocument();

        await user.click(screen.getByRole('button', { expanded: false }));

        // All 25 versions should be rendered
        const currentBadges = screen.getAllByText('Vigente');
        const supersededBadges = screen.getAllByText('Superada');
        expect(currentBadges).toHaveLength(1);
        expect(supersededBadges).toHaveLength(24);
    });
});
