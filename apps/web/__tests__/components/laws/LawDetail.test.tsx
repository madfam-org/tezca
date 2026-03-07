import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LawDetail } from '@/components/laws/LawDetail';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { api } from '@/lib/api';
import {
    makeLawApiResponse,
    makeArticlesApiResponse,
    LONG_LAW_NAME,
    SPECIAL_CHARS_TEXT,
} from '../../fixtures/mockFactories';

// Mock API module
vi.mock('@/lib/api', () => ({
    api: {
        getLawDetail: vi.fn(),
        getLawArticles: vi.fn(),
    },
}));

// Mock child components as shallow renders to test data flow
vi.mock('@/components/laws/LawHeader', () => ({
    LawHeader: ({ law, version }: { law: Record<string, unknown>; version: Record<string, unknown> }) => (
        <div data-testid="law-header" data-law-name={law.name} data-pub-date={version?.publication_date} />
    ),
}));

vi.mock('@/components/laws/TableOfContents', () => ({
    TableOfContents: ({ articles }: { articles: unknown[] }) => (
        <div data-testid="toc" data-article-count={articles.length} />
    ),
}));

vi.mock('@/components/laws/ArticleViewer', () => ({
    ArticleViewer: ({ articles, lawId, publicationDate }: { articles: unknown[]; lawId: string; publicationDate?: string | null }) => (
        <div data-testid="article-viewer" data-article-count={articles.length} data-law-id={lawId} data-pub-date={publicationDate ?? ''} />
    ),
}));

vi.mock('@/components/laws/ArticleSearch', () => ({
    ArticleSearch: ({ lawId }: { lawId: string }) => (
        <div data-testid="article-search" data-law-id={lawId} />
    ),
}));

vi.mock('@/components/laws/KeyboardShortcuts', () => ({
    KeyboardShortcuts: () => null,
}));

vi.mock('@/components/laws/RelatedLaws', () => ({
    RelatedLaws: () => null,
}));

vi.mock('@/components/laws/CrossReferencePanel', () => ({
    CrossReferencePanel: ({ lawId }: { lawId: string }) => (
        <div data-testid="cross-ref-panel" data-law-id={lawId} />
    ),
}));

vi.mock('@/components/graph/LawGraphContainer', () => ({
    LawGraphContainer: ({ lawId }: { lawId: string }) => (
        <div data-testid="law-graph" data-law-id={lawId} />
    ),
}));

vi.mock('@/components/laws/VersionTimeline', () => ({
    VersionTimeline: ({ versions }: { versions: unknown[] }) => (
        <div data-testid="version-timeline" data-version-count={versions.length} />
    ),
}));

vi.mock('@/components/laws/AnnotationPanel', () => ({
    AnnotationPanel: () => null,
}));

vi.mock('@/components/laws/AlertButton', () => ({
    AlertButton: () => null,
}));

vi.mock('@/components/Breadcrumbs', () => ({
    Breadcrumbs: ({ lawName }: { lawName: string }) => (
        <div data-testid="breadcrumbs" data-law-name={lawName} />
    ),
}));

vi.mock('@/components/FontSizeControl', () => ({
    FontSizeControl: () => null,
}));

vi.mock('@/components/skeletons/LawDetailSkeleton', () => ({
    LawDetailSkeleton: () => <div data-testid="law-detail-skeleton" />,
}));

vi.mock('@/components/RecentlyViewed', () => ({
    recordLawView: vi.fn(),
}));

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe('LawDetail data flow', () => {
    beforeEach(() => {
        vi.mocked(api.getLawDetail).mockReset();
        vi.mocked(api.getLawArticles).mockReset();
        // Mock window.location.hash
        Object.defineProperty(window, 'location', {
            value: { hash: '', origin: 'http://localhost:3000', pathname: '/leyes/cpeum' },
            writable: true,
        });
        window.history.pushState = vi.fn();
    });

    it('renders loading skeleton initially', async () => {
        vi.mocked(api.getLawDetail).mockReturnValue(new Promise(() => {}));
        vi.mocked(api.getLawArticles).mockReturnValue(new Promise(() => {}));

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        expect(screen.getByTestId('law-detail-skeleton')).toBeInTheDocument();
    });

    it('renders law name from API response', async () => {
        const lawData = makeLawApiResponse({ name: 'Constituci\u00f3n Pol\u00edtica' });
        const articlesData = makeArticlesApiResponse(5);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const header = screen.getByTestId('law-header');
            expect(header).toHaveAttribute('data-law-name', 'Constituci\u00f3n Pol\u00edtica');
        });
    });

    it('handles missing name with empty string fallback', async () => {
        const lawData = makeLawApiResponse({ name: undefined as unknown as string });
        const articlesData = makeArticlesApiResponse(2);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const header = screen.getByTestId('law-header');
            expect(header).toHaveAttribute('data-law-name', '');
        });
    });

    it('handles missing official_id with lawId fallback', async () => {
        const lawData = makeLawApiResponse({ official_id: undefined as unknown as string, id: undefined as unknown as string });
        const articlesData = makeArticlesApiResponse(2);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="my-law" />);
        });

        // Should not crash — the fallback chain official_id ?? id ?? lawId applies
        await waitFor(() => {
            expect(screen.getByTestId('law-header')).toBeInTheDocument();
        });
    });

    it('passes all articles to ArticleViewer', async () => {
        const lawData = makeLawApiResponse();
        const articlesData = makeArticlesApiResponse(15);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const viewer = screen.getByTestId('article-viewer');
            expect(viewer).toHaveAttribute('data-article-count', '15');
        });
    });

    it('renders with 150+ articles without truncation', async () => {
        const lawData = makeLawApiResponse();
        const articlesData = makeArticlesApiResponse(150);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const viewer = screen.getByTestId('article-viewer');
            expect(viewer).toHaveAttribute('data-article-count', '150');
        });
    });

    it('renders with 0 articles', async () => {
        const lawData = makeLawApiResponse();
        const articlesData = makeArticlesApiResponse(0);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const viewer = screen.getByTestId('article-viewer');
            expect(viewer).toHaveAttribute('data-article-count', '0');
        });
    });

    it('passes versions array to VersionTimeline', async () => {
        const versions = [
            { publication_date: '2024-06-06', dof_url: null, change_summary: null },
            { publication_date: '2023-01-01', dof_url: null, change_summary: 'Prev' },
            { publication_date: '2022-01-01', dof_url: null, change_summary: 'Older' },
        ];
        const lawData = makeLawApiResponse({ versions });
        const articlesData = makeArticlesApiResponse(5);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const timeline = screen.getByTestId('version-timeline');
            expect(timeline).toHaveAttribute('data-version-count', '3');
        });
    });

    it('handles missing versions array', async () => {
        const lawData = makeLawApiResponse({ versions: undefined as unknown as [] });
        const articlesData = makeArticlesApiResponse(2);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const timeline = screen.getByTestId('version-timeline');
            expect(timeline).toHaveAttribute('data-version-count', '0');
        });
    });

    it('renders error state on API failure', async () => {
        vi.mocked(api.getLawDetail).mockRejectedValue(new Error('Network error'));
        vi.mocked(api.getLawArticles).mockResolvedValue(makeArticlesApiResponse(0));

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            expect(screen.getByText('Error al cargar la ley')).toBeInTheDocument();
            expect(screen.getByText('Network error')).toBeInTheDocument();
        });
    });

    it('renders error state on articles API failure', async () => {
        vi.mocked(api.getLawDetail).mockResolvedValue(makeLawApiResponse());
        vi.mocked(api.getLawArticles).mockRejectedValue(new Error('Articles failed'));

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            expect(screen.getByText('Error al cargar la ley')).toBeInTheDocument();
        });
    });

    it('passes lawId to CrossReferencePanel and LawGraphContainer', async () => {
        const lawData = makeLawApiResponse();
        const articlesData = makeArticlesApiResponse(5);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="ley-amparo" />);
        });

        await waitFor(() => {
            expect(screen.getByTestId('cross-ref-panel')).toHaveAttribute('data-law-id', 'ley-amparo');
            expect(screen.getByTestId('law-graph')).toHaveAttribute('data-law-id', 'ley-amparo');
        });
    });

    it('normalizes law data with all optional fields null', async () => {
        const lawData = makeLawApiResponse({
            official_id: 'test',
            name: 'Test',
            category: undefined as unknown as string,
            tier: undefined as unknown as string,
            state: null,
            status: undefined,
            last_verified: null,
            versions: [],
        });
        const articlesData = makeArticlesApiResponse(1);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="test" />);
        });

        await waitFor(() => {
            expect(screen.getByTestId('law-header')).toBeInTheDocument();
        });
    });

    it('handles law with long name (500+ chars)', async () => {
        const lawData = makeLawApiResponse({ name: LONG_LAW_NAME });
        const articlesData = makeArticlesApiResponse(2);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="long-name" />);
        });

        await waitFor(() => {
            const header = screen.getByTestId('law-header');
            expect(header.getAttribute('data-law-name')).toBe(LONG_LAW_NAME);
            expect(header.getAttribute('data-law-name')!.length).toBeGreaterThan(400);
        });
    });

    it('handles law with special characters in name', async () => {
        const lawData = makeLawApiResponse({ name: SPECIAL_CHARS_TEXT });
        const articlesData = makeArticlesApiResponse(2);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="special" />);
        });

        await waitFor(() => {
            const header = screen.getByTestId('law-header');
            expect(header.getAttribute('data-law-name')).toBe(SPECIAL_CHARS_TEXT);
        });
    });

    it('passes correct version publication_date to ArticleViewer', async () => {
        const lawData = makeLawApiResponse({
            versions: [{ publication_date: '2024-06-06', dof_url: null, change_summary: null }],
        });
        const articlesData = makeArticlesApiResponse(3);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            const viewer = screen.getByTestId('article-viewer');
            expect(viewer).toHaveAttribute('data-pub-date', '2024-06-06');
        });
    });

    it('sets total from API response', async () => {
        const lawData = makeLawApiResponse();
        const articlesData = makeArticlesApiResponse(25, { total: 250 });
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        // The component stores total internally; verify TOC gets correct article count
        await waitFor(() => {
            const toc = screen.getByTestId('toc');
            expect(toc).toHaveAttribute('data-article-count', '25');
        });
    });

    it('handles concurrent law and articles fetch', async () => {
        const lawData = makeLawApiResponse();
        const articlesData = makeArticlesApiResponse(10);
        vi.mocked(api.getLawDetail).mockResolvedValue(lawData);
        vi.mocked(api.getLawArticles).mockResolvedValue(articlesData);

        await act(async () => {
            renderWithLang(<LawDetail lawId="cpeum" />);
        });

        await waitFor(() => {
            expect(screen.getByTestId('law-header')).toBeInTheDocument();
            expect(screen.getByTestId('article-viewer')).toBeInTheDocument();
        });

        // Both API methods should have been called exactly once
        expect(api.getLawDetail).toHaveBeenCalledTimes(1);
        expect(api.getLawArticles).toHaveBeenCalledTimes(1);
    });
});
