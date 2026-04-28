/**
 * Skeleton components are pure presentational placeholders that render
 * during loading states. Tests verify they render without crashing and
 * use the expected animate-pulse class for the loading shimmer.
 */

import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DashboardSkeleton } from '@/components/skeletons/DashboardSkeleton';
import { LawDetailSkeleton } from '@/components/skeletons/LawDetailSkeleton';
import { SearchResultsSkeleton } from '@/components/skeletons/SearchResultsSkeleton';

describe('DashboardSkeleton', () => {
    it('renders 4 metric placeholders', () => {
        const { container } = render(<DashboardSkeleton />);
        const cards = container.querySelectorAll('.h-24.rounded-xl.bg-muted');
        expect(cards).toHaveLength(4);
    });

    it('uses animate-pulse for the loading shimmer', () => {
        const { container } = render(<DashboardSkeleton />);
        expect(container.firstChild).toHaveClass('animate-pulse');
    });
});

describe('SearchResultsSkeleton', () => {
    it('renders 5 result placeholders', () => {
        const { container } = render(<SearchResultsSkeleton />);
        const cards = container.querySelectorAll('.rounded-lg.border.bg-card');
        expect(cards).toHaveLength(5);
    });

    it('uses animate-pulse', () => {
        const { container } = render(<SearchResultsSkeleton />);
        expect(container.firstChild).toHaveClass('animate-pulse');
    });
});

describe('LawDetailSkeleton', () => {
    it('renders 4 article placeholders + a TOC sidebar', () => {
        const { container } = render(<LawDetailSkeleton />);
        // 4 article cards in <main>
        const articles = container.querySelectorAll('main .bg-card.border.rounded-lg');
        expect(articles).toHaveLength(4);
        // 8 TOC line widths in <aside>
        const tocLines = container.querySelectorAll('aside .h-4.rounded.bg-muted');
        expect(tocLines).toHaveLength(8);
    });

    it('uses animate-pulse', () => {
        const { container } = render(<LawDetailSkeleton />);
        expect(container.firstChild).toHaveClass('animate-pulse');
    });
});
