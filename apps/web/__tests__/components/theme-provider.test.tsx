import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const mockSetTheme = vi.fn();
const mockUseTheme = vi.fn(() => ({ setTheme: mockSetTheme, theme: 'light' }));

vi.mock('next-themes', () => ({
    useTheme: () => mockUseTheme(),
    ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { ModeToggle } from '@/components/mode-toggle';
import { ThemeProvider } from '@/components/theme-provider';

describe('ThemeProvider', () => {
    it('renders children verbatim', () => {
        render(
            <ThemeProvider>
                <div>passthrough</div>
            </ThemeProvider>,
        );
        expect(screen.getByText('passthrough')).toBeInTheDocument();
    });
});

describe('ModeToggle', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseTheme.mockReturnValue({ setTheme: mockSetTheme, theme: 'light' });
    });

    it('renders the toggle button', () => {
        render(<ModeToggle />);
        const button = screen.getByRole('button');
        expect(button).toBeInTheDocument();
        expect(button).toHaveAttribute('title', 'Toggle theme');
    });

    it('exposes screen-reader text', () => {
        render(<ModeToggle />);
        expect(screen.getByText('Toggle theme', { selector: 'span' })).toBeInTheDocument();
    });

    it('switches from light to dark on click', () => {
        mockUseTheme.mockReturnValue({ setTheme: mockSetTheme, theme: 'light' });
        render(<ModeToggle />);
        fireEvent.click(screen.getByRole('button'));
        expect(mockSetTheme).toHaveBeenCalledWith('dark');
    });

    it('switches from dark to light on click', () => {
        mockUseTheme.mockReturnValue({ setTheme: mockSetTheme, theme: 'dark' });
        render(<ModeToggle />);
        fireEvent.click(screen.getByRole('button'));
        expect(mockSetTheme).toHaveBeenCalledWith('light');
    });
});
