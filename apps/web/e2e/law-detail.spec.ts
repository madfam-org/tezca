import { test, expect } from './fixtures';

test.describe('Law detail page', () => {
    test('renders law header and articles', async ({ page }) => {
        await page.goto('/laws/ley-federal-del-trabajo');

        // Law name renders in the header
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();

        // Articles render
        await expect(page.getByText('Art. 1').first()).toBeVisible();
        await expect(page.getByText(/La presente Ley es de observancia general/).first()).toBeVisible();
    });

    test('table of contents renders article entries', async ({ page }) => {
        await page.goto('/laws/ley-federal-del-trabajo');

        // Wait for articles to load
        await expect(page.getByText('Art. 1').first()).toBeVisible();

        // TOC should list articles (they appear as clickable items)
        const tocItems = page.locator('aside').getByText(/Art\./);
        await expect(tocItems.first()).toBeVisible();
    });

    test('clicking TOC item updates URL hash', async ({ page }) => {
        await page.goto('/laws/ley-federal-del-trabajo');

        // Wait for content to load
        await expect(page.getByText('Art. 2').first()).toBeVisible();

        // Click an article in the TOC sidebar
        await page.locator('aside').getByText('Art. 2').first().click();

        // URL hash includes the full article_id "Art. 2" (URL-encoded)
        await expect(page).toHaveURL(/article-Art/);
    });

    test('direct hash navigation highlights article', async ({ page }) => {
        await page.goto('/laws/ley-federal-del-trabajo#article-2');

        // Page loads and articles are visible
        await expect(page.getByText('Art. 2').first()).toBeVisible();
        await expect(page.getByText(/Las normas del trabajo tienden/).first()).toBeVisible();
    });

    test('error state renders when law not found', async ({ page }) => {
        // Override the mock for a non-existent law
        await page.route('**/api/v1/laws/nonexistent/', (route) =>
            route.fulfill({ status: 404, json: { detail: 'Not found' } })
        );

        await page.goto('/laws/nonexistent');

        await expect(page.getByText(/Error al cargar la ley/)).toBeVisible();
        await expect(page.getByText('Volver al buscador')).toBeVisible();
    });
});
