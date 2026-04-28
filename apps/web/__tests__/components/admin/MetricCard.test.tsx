import { render, screen } from '@testing-library/react';
import { Activity } from 'lucide-react';
import { describe, expect, it } from 'vitest';

import { MetricCard } from '@/components/admin/MetricCard';

describe('MetricCard', () => {
    it('renders title and value', () => {
        render(<MetricCard title="Active Laws" value={1000} />);
        expect(screen.getByText('Active Laws')).toBeInTheDocument();
        expect(screen.getByText('1000')).toBeInTheDocument();
    });

    it('renders trend with positive color when prefixed with +', () => {
        render(<MetricCard title="X" value={5} trend="+12%" />);
        const trendEl = screen.getByText('+12%');
        expect(trendEl.className).toMatch(/text-green/);
    });

    it('renders trend with negative color when prefixed with -', () => {
        render(<MetricCard title="X" value={5} trend="-3%" />);
        const trendEl = screen.getByText('-3%');
        expect(trendEl.className).toMatch(/text-red/);
    });

    it('renders trend with muted color when no +/- prefix', () => {
        render(<MetricCard title="X" value={5} trend="stable" />);
        const trendEl = screen.getByText('stable');
        expect(trendEl.className).toMatch(/text-muted-foreground/);
    });

    it('applies success status to value text', () => {
        render(<MetricCard title="X" value={1} status="success" />);
        const valueEl = screen.getByText('1');
        expect(valueEl.className).toMatch(/text-green/);
    });

    it('applies error status to value text', () => {
        render(<MetricCard title="X" value={1} status="error" />);
        const valueEl = screen.getByText('1');
        expect(valueEl.className).toMatch(/text-red/);
    });

    it('renders the description when provided', () => {
        render(<MetricCard title="X" value={1} description="Last 24h" />);
        expect(screen.getByText('Last 24h')).toBeInTheDocument();
    });

    it('renders the icon when provided', () => {
        const { container } = render(<MetricCard title="X" value={1} icon={Activity} />);
        // Lucide icons render as SVGs
        const svg = container.querySelector('svg');
        expect(svg).not.toBeNull();
    });

    it('renders without crashing when only required props are passed', () => {
        render(<MetricCard title="Minimal" value={42} />);
        expect(screen.getByText('Minimal')).toBeInTheDocument();
    });

    it('handles string values', () => {
        render(<MetricCard title="X" value="N/A" />);
        expect(screen.getByText('N/A')).toBeInTheDocument();
    });
});
