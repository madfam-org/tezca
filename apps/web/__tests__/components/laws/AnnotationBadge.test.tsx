import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AnnotationBadge } from '@/components/laws/AnnotationBadge';

describe('AnnotationBadge', () => {
    it('renders nothing when count is zero', () => {
        const { container } = render(<AnnotationBadge count={0} onClick={() => {}} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders the count when count > 0', () => {
        render(<AnnotationBadge count={5} onClick={() => {}} />);
        expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('exposes the count via aria-label', () => {
        render(<AnnotationBadge count={3} onClick={() => {}} />);
        expect(screen.getByLabelText('3 annotations')).toBeInTheDocument();
    });

    it('invokes onClick when clicked', () => {
        const onClick = vi.fn();
        render(<AnnotationBadge count={2} onClick={onClick} />);
        fireEvent.click(screen.getByRole('button'));
        expect(onClick).toHaveBeenCalledOnce();
    });

    it('applies custom className alongside built-in styles', () => {
        render(<AnnotationBadge count={1} onClick={() => {}} className="my-extra-class" />);
        const button = screen.getByRole('button');
        expect(button.className).toContain('my-extra-class');
    });
});
