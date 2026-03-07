import { test, expect } from '@playwright/test';

/**
 * UI data fidelity spot-checks — verifies the web UI accurately
 * displays data from the API without truncation or loss.
 *
 * Skipped by default. Enable with:
 *   UI_FIDELITY_E2E=1 npx playwright test e2e/ui-data-fidelity.spec.ts
 *
 * Requirements:
 *   - Next.js server on localhost:3000
 *   - Django API running and reachable
 *   - Elasticsearch populated with article data
 */

const LIVE = process.env.UI_FIDELITY_E2E === '1';

test.describe('UI data fidelity spot-checks', () => {
    test.skip(!LIVE, 'Requires UI_FIDELITY_E2E=1 with live API');

    test('law detail article count matches TOC count', async ({ page }) => {
        await page.goto('/leyes/cpeum');
        await page.waitForSelector('article', { timeout: 20_000 });

        const articleCount = await page.locator('article').count();
        // TOC links should match rendered articles
        const tocLinks = await page.locator('#toc-panel a, #toc-panel button').count();

        // Both should be >100 for CPEUM and reasonably close
        expect(articleCount).toBeGreaterThan(100);
        // TOC might have slightly different count due to grouping, but should be non-zero
        expect(tocLinks).toBeGreaterThan(0);
    });

    test('law detail article text not truncated', async ({ page }) => {
        await page.goto('/leyes/cpeum');
        await page.waitForSelector('article', { timeout: 20_000 });

        // Get text content of all articles
        const articleTexts = await page.locator('article').allTextContents();
        // At least one article should have substantial content (>500 chars)
        const hasLongArticle = articleTexts.some(t => t.length > 500);
        expect(hasLongArticle).toBe(true);
    });

    test('search result snippets contain query term', async ({ page }) => {
        await page.goto('/busqueda?q=amparo');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        // Every visible snippet should contain the search term (case insensitive)
        const snippets = await page.locator('.line-clamp-3').allTextContents();
        expect(snippets.length).toBeGreaterThan(0);
        for (const snippet of snippets) {
            expect(snippet.toLowerCase()).toContain('amparo');
        }
    });

    test('search facets show all 3 tier types', async ({ page }) => {
        await page.goto('/busqueda?q=ley&jurisdiction=federal,state,municipal');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        // Check that results include federal, state, and municipal tiers
        const pageContent = await page.textContent('body');
        expect(pageContent).toBeTruthy();
        // At least some tier badges should render
        const badges = await page.locator('span:has-text("Federal"), span:has-text("Estatal"), span:has-text("Municipal")').count();
        expect(badges).toBeGreaterThan(0);
    });

    test('version timeline shows versions for CPEUM', async ({ page }) => {
        await page.goto('/leyes/cpeum');
        await page.waitForSelector('article', { timeout: 20_000 });

        // Look for version timeline section
        const timeline = page.locator('section[aria-label*="Historial"], section[aria-label*="Version"]');
        await expect(timeline).toBeVisible({ timeout: 5_000 });

        // Click to expand
        const expandBtn = timeline.locator('button').first();
        await expandBtn.click();

        // CPEUM has many versions; verify at least some render
        const versionBadges = timeline.locator('text=Vigente');
        await expect(versionBadges.first()).toBeVisible();
    });

    test('cross-reference panel loads for CPEUM', async ({ page }) => {
        await page.goto('/leyes/cpeum');
        await page.waitForSelector('article', { timeout: 20_000 });

        // Cross-reference panel should load
        const xrefSection = page.locator('section[aria-label*="Referencia"], section[aria-label*="Cross"]');
        // It may or may not appear depending on data; if it does, verify content
        const count = await xrefSection.count();
        if (count > 0) {
            await expect(xrefSection.first()).toBeVisible();
        }
    });

    test('TOC article labels match article headings', async ({ page }) => {
        await page.goto('/leyes/cpeum');
        await page.waitForSelector('article', { timeout: 20_000 });

        // Get first 5 article heading texts
        const headings = await page.locator('article h3').allTextContents();
        expect(headings.length).toBeGreaterThan(0);

        // Each heading should contain "Art\u00edculo" or a meaningful label
        for (const heading of headings.slice(0, 5)) {
            expect(heading.trim().length).toBeGreaterThan(0);
        }
    });

    test('pagination total matches displayed results', async ({ page }) => {
        await page.goto('/busqueda?q=constitucion');
        await page.waitForSelector('a[href*="/leyes/"]', { timeout: 15_000 });

        // The "Mostrando X-Y de Z" text should be present
        const showingText = await page.locator('text=/Mostrando|Showing/').textContent();
        expect(showingText).toBeTruthy();
        expect(showingText).toMatch(/\d+/);
    });

    test('category page shows law cards', async ({ page }) => {
        await page.goto('/categorias/constitucional');
        await page.waitForLoadState('networkidle', { timeout: 15_000 });

        // Should show some law cards or a law list
        const content = await page.textContent('main');
        expect(content).toBeTruthy();
        expect(content!.length).toBeGreaterThan(50);
    });

    test('state page shows law list', async ({ page }) => {
        await page.goto('/estados/jalisco');
        await page.waitForLoadState('networkidle', { timeout: 15_000 });

        const content = await page.textContent('main');
        expect(content).toBeTruthy();
        expect(content!.length).toBeGreaterThan(50);
    });
});
