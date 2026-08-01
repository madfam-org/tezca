import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// AuthModal now renders SignIn/SignUp from @janua/nextjs — stub them so the
// modal mounts without the real SDK (which needs a JanuaProvider).
vi.mock('@janua/nextjs', () => ({
    SignIn: (_props: any) => <div data-testid="sign-in" />,
    SignUp: (_props: any) => <div data-testid="sign-up" />,
}));

import { AuthModal } from '@/components/AuthModal';

describe('AuthModal', () => {
    const onClose = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders nothing when closed', () => {
        const { container } = render(<AuthModal open={false} onClose={onClose} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders modal when open', () => {
        render(<AuthModal open={true} onClose={onClose} />);
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Iniciar sesión')).toBeInTheDocument();
    });

    it('calls onClose when close button clicked', () => {
        render(<AuthModal open={true} onClose={onClose} />);
        fireEvent.click(screen.getByLabelText('Cerrar'));
        expect(onClose).toHaveBeenCalledOnce();
    });

    it('calls onClose when backdrop clicked', () => {
        render(<AuthModal open={true} onClose={onClose} />);
        // Backdrop is the first div with aria-hidden
        const backdrop = screen.getByRole('dialog').querySelector('[aria-hidden="true"]')!;
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalledOnce();
    });

    it('calls onClose on Escape key', () => {
        render(<AuthModal open={true} onClose={onClose} />);
        fireEvent.keyDown(document, { key: 'Escape' });
        expect(onClose).toHaveBeenCalledOnce();
    });
});
