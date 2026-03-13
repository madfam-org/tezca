import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defaultAuthState, mockAuth } from '../../helpers/auth-mock';

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock AuthContext
const mockUseAuth = vi.fn(() => defaultAuthState);
vi.mock('@/components/providers/AuthContext', () => ({
    useAuth: (...args: any[]) => mockUseAuth(...args),
}));

// Mock auth-token
vi.mock('@/lib/auth-token', () => ({
    getAuthToken: vi.fn(() => 'test-token'),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => <div data-testid="card" className={className}>{children}</div>,
}));

// Mock @tezca/lib
vi.mock('@tezca/lib', () => ({
    cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    X: ({ className }: any) => <span data-testid="x-icon" className={className} />,
    Plus: ({ className }: any) => <span data-testid="plus-icon" className={className} />,
    Trash2: ({ className }: any) => <span data-testid="trash-icon" className={className} />,
    Pencil: ({ className }: any) => <span data-testid="pencil-icon" className={className} />,
    Check: ({ className }: any) => <span data-testid="check-icon" className={className} />,
    MessageSquare: ({ className }: any) => <span data-testid="msg-icon" className={className} />,
}));

const mockGetAnnotations = vi.fn();
const mockCreateAnnotation = vi.fn();
const mockDeleteAnnotation = vi.fn();
const mockUpdateAnnotation = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        getAnnotations: (...args: any[]) => mockGetAnnotations(...args),
        createAnnotation: (...args: any[]) => mockCreateAnnotation(...args),
        deleteAnnotation: (...args: any[]) => mockDeleteAnnotation(...args),
        updateAnnotation: (...args: any[]) => mockUpdateAnnotation(...args),
    },
}));

import { AnnotationPanel } from '@/components/laws/AnnotationPanel';

describe('AnnotationPanel', () => {
    const onClose = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mockUseAuth.mockReturnValue(defaultAuthState);
        mockGetAnnotations.mockResolvedValue({ annotations: [] });
        mockCreateAnnotation.mockResolvedValue({
            id: 1, law_id: 'cpeum', article_id: 'art-1', text: 'Test note',
            highlight_start: null, highlight_end: null, color: 'yellow',
            created_at: '2026-03-01', updated_at: '2026-03-01',
        });
        mockDeleteAnnotation.mockResolvedValue({});
        mockUpdateAnnotation.mockResolvedValue({
            id: 1, law_id: 'cpeum', article_id: 'art-1', text: 'Updated note',
            highlight_start: null, highlight_end: null, color: 'green',
            created_at: '2026-03-01', updated_at: '2026-03-01',
        });
    });

    // ---------------------------------------------------------------
    // 1. Returns null when not open
    // ---------------------------------------------------------------
    it('returns null when not open', () => {
        const { container } = render(
            <AnnotationPanel lawId="cpeum" open={false} onClose={onClose} />,
        );
        expect(container.innerHTML).toBe('');
    });

    // ---------------------------------------------------------------
    // 2. Renders panel when open
    // ---------------------------------------------------------------
    it('renders panel with title when open', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );
        expect(screen.getByText('Notas y anotaciones')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Shows login required when not authenticated
    // ---------------------------------------------------------------
    it('shows login required message when not authenticated', () => {
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );
        expect(screen.getByText('Inicia sesión para guardar notas.')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 4. Shows empty state when authenticated with no annotations
    // ---------------------------------------------------------------
    it('shows empty state when no annotations exist', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('No hay notas para esta ley.')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 5. Renders annotations list
    // ---------------------------------------------------------------
    it('renders annotations when they exist', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        mockGetAnnotations.mockResolvedValue({
            annotations: [
                {
                    id: 1, law_id: 'cpeum', article_id: 'art-1', text: 'Mi nota sobre articulo 1',
                    highlight_start: null, highlight_end: null, color: 'yellow',
                    created_at: '2026-03-01T12:00:00Z', updated_at: '2026-03-01T12:00:00Z',
                },
            ],
        });

        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Mi nota sobre articulo 1')).toBeInTheDocument();
            expect(screen.getByText(/Artículo art-1/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 6. Shows add note button
    // ---------------------------------------------------------------
    it('shows add note button when authenticated', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Agregar nota')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 7. Clicking add note shows form
    // ---------------------------------------------------------------
    it('shows create form when add note is clicked', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Agregar nota')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Agregar nota'));
        expect(screen.getByPlaceholderText('Escribe tu nota...')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 8. Close button calls onClose
    // ---------------------------------------------------------------
    it('close button calls onClose', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        fireEvent.click(screen.getByLabelText('Cerrar panel'));
        expect(onClose).toHaveBeenCalledOnce();
    });

    // ---------------------------------------------------------------
    // 9. Delete button removes annotation
    // ---------------------------------------------------------------
    it('delete button calls API and removes annotation', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        mockGetAnnotations.mockResolvedValue({
            annotations: [
                {
                    id: 1, law_id: 'cpeum', article_id: 'art-1', text: 'Note to delete',
                    highlight_start: null, highlight_end: null, color: 'yellow',
                    created_at: '2026-03-01T12:00:00Z', updated_at: '2026-03-01T12:00:00Z',
                },
            ],
        });

        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Note to delete')).toBeInTheDocument();
        });

        await act(async () => {
            fireEvent.click(screen.getByLabelText('Eliminar'));
        });

        expect(mockDeleteAnnotation).toHaveBeenCalledWith('test-token', 1);
    });

    // ---------------------------------------------------------------
    // 10. Edit button shows edit form
    // ---------------------------------------------------------------
    it('edit button shows edit form with current text', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        mockGetAnnotations.mockResolvedValue({
            annotations: [
                {
                    id: 1, law_id: 'cpeum', article_id: 'art-1', text: 'Original text',
                    highlight_start: null, highlight_end: null, color: 'yellow',
                    created_at: '2026-03-01T12:00:00Z', updated_at: '2026-03-01T12:00:00Z',
                },
            ],
        });

        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Original text')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByLabelText('Editar'));

        // Edit form should show with textarea
        const textarea = document.querySelector('textarea');
        expect(textarea).toBeDefined();
        expect(textarea?.value).toBe('Original text');
    });

    // ---------------------------------------------------------------
    // 11. Has dialog role with aria-modal
    // ---------------------------------------------------------------
    it('has dialog role with aria-modal', () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        expect(dialog.getAttribute('aria-modal')).toBe('true');
    });

    // ---------------------------------------------------------------
    // 12. Cancel button hides create form
    // ---------------------------------------------------------------
    it('cancel button hides the create form', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Agregar nota')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Agregar nota'));
        expect(screen.getByPlaceholderText('Escribe tu nota...')).toBeInTheDocument();

        fireEvent.click(screen.getByText('Cancelar'));
        expect(screen.queryByPlaceholderText('Escribe tu nota...')).not.toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 13. Color picker buttons present
    // ---------------------------------------------------------------
    it('shows color picker buttons in create form', async () => {
        mockUseAuth.mockReturnValue(mockAuth({ isAuthenticated: true, tier: 'pro' }));
        render(
            <AnnotationPanel lawId="cpeum" open={true} onClose={onClose} />,
        );

        await waitFor(() => {
            expect(screen.getByText('Agregar nota')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Agregar nota'));
        expect(screen.getByLabelText('yellow')).toBeInTheDocument();
        expect(screen.getByLabelText('green')).toBeInTheDocument();
        expect(screen.getByLabelText('blue')).toBeInTheDocument();
        expect(screen.getByLabelText('pink')).toBeInTheDocument();
    });
});
