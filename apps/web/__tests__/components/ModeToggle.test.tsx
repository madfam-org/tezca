import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

const mockSetTheme = vi.fn();
vi.mock('next-themes', () => ({
    useTheme: () => ({ theme: 'light', setTheme: mockSetTheme }),
}));
vi.mock('lucide-react', () => ({
    Sun: (props: any) => <svg data-testid="sun-icon" {...props} />,
    Moon: (props: any) => <svg data-testid="moon-icon" {...props} />,
}));
vi.mock('@tezca/ui', () => ({
    Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

import { ModeToggle } from '@/components/mode-toggle';

describe('ModeToggle', () => {
    it('renders toggle button', () => {
        render(<ModeToggle />);
        expect(screen.getByTitle('Toggle theme')).toBeInTheDocument();
    });

    it('calls setTheme on click', () => {
        render(<ModeToggle />);
        fireEvent.click(screen.getByTitle('Toggle theme'));
        expect(mockSetTheme).toHaveBeenCalledWith('dark');
    });
});
