import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: vi.fn(() => ({
        isAuthenticated: false,
        tier: 'anon' as const,
        loginUrl: '/auth/login',
    })),
}));

vi.mock('@/lib/config', () => ({
    API_BASE_URL: 'http://localhost:8000',
}));

import { ExportDropdown } from '@/components/laws/ExportDropdown';
import { useAuth } from '@/components/providers/AuthContext';

describe('ExportDropdown', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: false,
            tier: 'anon',
            loginUrl: '/auth/login',
            userId: null,
            email: null,
            name: null,
            signOut: vi.fn(),
        });
    });

    it('renders the download button', () => {
        render(<ExportDropdown lawId="cpeum" />);
        const btn = screen.getByRole('button', { expanded: false });
        expect(btn).toBeInTheDocument();
    });

    it('opens dropdown on click', () => {
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        expect(screen.getByText('Descargar TXT')).toBeInTheDocument();
        expect(screen.getByText('Descargar PDF')).toBeInTheDocument();
        expect(screen.getByText('Descargar LaTeX')).toBeInTheDocument();
        expect(screen.getByText('Descargar DOCX')).toBeInTheDocument();
        expect(screen.getByText('Descargar EPUB')).toBeInTheDocument();
        expect(screen.getByText('Descargar JSON')).toBeInTheDocument();
    });

    it('shows all 6 format buttons', () => {
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        // 6 format buttons + 1 toggle button = 7 buttons
        const buttons = screen.getAllByRole('button');
        expect(buttons).toHaveLength(7);
    });

    it('shows Cuenta badge on PDF', () => {
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        expect(screen.getByText('Cuenta')).toBeInTheDocument();
    });

    it('shows Premium badges on premium formats', () => {
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        expect(screen.getAllByText('Premium')).toHaveLength(4);
    });

    it('shows login message when anon clicks PDF', () => {
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        fireEvent.click(screen.getByText('Descargar PDF'));
        expect(screen.getByText('Inicia sesión para descargar en este formato')).toBeInTheDocument();
        expect(screen.getByText('Iniciar sesión')).toBeInTheDocument();
    });

    it('shows login message when anon clicks premium format', () => {
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        fireEvent.click(screen.getByText('Descargar LaTeX'));
        expect(screen.getByText('Inicia sesión para descargar en este formato')).toBeInTheDocument();
    });

    it('shows upgrade message when free-tier clicks premium format', () => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: true,
            tier: 'free',
            loginUrl: '/auth/login',
            userId: null,
            email: null,
            name: null,
            signOut: vi.fn(),
        });
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        fireEvent.click(screen.getByText('Descargar DOCX'));
        expect(screen.getByText('Formato Premium — Actualiza tu cuenta')).toBeInTheDocument();
    });

    it('downloads TXT for anonymous users', async () => {
        const mockBlob = new Blob(['test content'], { type: 'text/plain' });
        const mockFetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            blob: () => Promise.resolve(mockBlob),
        });
        global.fetch = mockFetch;
        global.URL.createObjectURL = vi.fn(() => 'blob:test');
        global.URL.revokeObjectURL = vi.fn();

        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        fireEvent.click(screen.getByText('Descargar TXT'));

        await waitFor(() => {
            expect(mockFetch).toHaveBeenCalledWith(
                'http://localhost:8000/laws/cpeum/export/txt/',
                expect.any(Object),
            );
        });
    });

    it('allows PDF download for free-tier users', async () => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: true,
            tier: 'free',
            loginUrl: '/auth/login',
            userId: null,
            email: null,
            name: null,
            signOut: vi.fn(),
        });
        const mockBlob = new Blob(['pdf'], { type: 'application/pdf' });
        const mockFetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            blob: () => Promise.resolve(mockBlob),
        });
        global.fetch = mockFetch;
        global.URL.createObjectURL = vi.fn(() => 'blob:test');
        global.URL.revokeObjectURL = vi.fn();

        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        fireEvent.click(screen.getByText('Descargar PDF'));

        await waitFor(() => {
            expect(mockFetch).toHaveBeenCalledWith(
                'http://localhost:8000/laws/cpeum/export/pdf/',
                expect.any(Object),
            );
        });
    });

    it('allows all formats for premium users', () => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: true,
            tier: 'premium',
            loginUrl: '/auth/login',
            userId: null,
            email: null,
            name: null,
            signOut: vi.fn(),
        });
        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        // No lock icons should be visible — all formats accessible
        // Click EPUB — should not show any message
        fireEvent.click(screen.getByText('Descargar EPUB'));
        expect(screen.queryByText('Inicia sesión para descargar en este formato')).not.toBeInTheDocument();
        expect(screen.queryByText('Formato Premium — Actualiza tu cuenta')).not.toBeInTheDocument();
    });

    it('shows rate limit message on 429', async () => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: false,
            tier: 'anon',
            loginUrl: '/auth/login',
            userId: null,
            email: null,
            name: null,
            signOut: vi.fn(),
        });
        const mockFetch = vi.fn().mockResolvedValue({
            ok: false,
            status: 429,
            json: () => Promise.resolve({ retry_after: 600 }),
        });
        global.fetch = mockFetch;

        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        fireEvent.click(screen.getByText('Descargar TXT'));

        await waitFor(() => {
            expect(screen.getByText(/Has alcanzado el límite/)).toBeInTheDocument();
            expect(screen.getByText(/10 minutos/)).toBeInTheDocument();
        });
    });

    it('handles 403 from server for unauthenticated user', async () => {
        const mockFetch = vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: () => Promise.resolve({ error: 'Authentication required', required_tier: 'free' }),
        });
        global.fetch = mockFetch;

        render(<ExportDropdown lawId="cpeum" />);
        fireEvent.click(screen.getByRole('button', { expanded: false }));
        // Manually force a fetch for TXT (anon should be allowed, but server returns 403)
        fireEvent.click(screen.getByText('Descargar TXT'));

        await waitFor(() => {
            expect(screen.getByText('Inicia sesión para descargar en este formato')).toBeInTheDocument();
        });
    });
});
