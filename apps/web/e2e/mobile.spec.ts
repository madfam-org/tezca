import { test, expect } from '@playwright/test';

test.describe('Mobile experience', () => {
    test.use({ viewport: { width: 390, height: 844 } }); // iPhone 14 viewport

    test('hamburger menu opens and closes', async ({ page }) => {
        await page.goto('/');
        const menuButton = page.getByRole('button', { name: /menú|menu/i });
        await expect(menuButton).toBeVisible();

        // Open menu
        await menuButton.click();
        await expect(menuButton).toHaveAttribute('aria-expanded', 'true');

        // Nav links visible in mobile panel
        const navPanel = page.locator('.md\\:hidden.border-t');
        await expect(navPanel).toBeVisible();

        // Close menu
        await menuButton.click();
        await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    });

    test('search results are scrollable', async ({ page }) => {
        await page.goto('/busqueda?q=trabajo');
        // Wait for results or empty state
        await page.waitForSelector('[data-testid="search-results"], [role="status"]', {
            timeout: 10000,
        }).catch(() => {});

        // Page should not have horizontal overflow
        const hasHorizontalScroll = await page.evaluate(() => {
            return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });
        expect(hasHorizontalScroll).toBe(false);
    });

    test('command search button is visible (no Cmd+K on mobile)', async ({ page }) => {
        await page.goto('/');
        // The search trigger should be a visible button
        const searchTrigger = page.locator('[aria-label*="uscar"], [aria-label*="earch"]').first();
        await expect(searchTrigger).toBeVisible();
    });

    test('law detail page is readable at small viewport', async ({ page }) => {
        await page.goto('/leyes');
        // Wait for law list
        const firstLaw = page.locator('a[href^="/leyes/"]').first();
        if (await firstLaw.isVisible()) {
            await firstLaw.click();
            await page.waitForLoadState('networkidle');

            // Text should be readable (min 12px)
            const smallText = await page.evaluate(() => {
                const elements = document.querySelectorAll('p, span, div');
                let tooSmall = 0;
                elements.forEach((el) => {
                    const fontSize = parseFloat(getComputedStyle(el).fontSize);
                    if (fontSize < 12 && el.textContent?.trim()) tooSmall++;
                });
                return tooSmall;
            });
            // Allow some small text (badges, labels) but flag excessive
            expect(smallText).toBeLessThan(10);
        }
    });

    test('no content is cut off horizontally', async ({ page }) => {
        const pages = ['/', '/leyes', '/categorias', '/estados'];
        for (const url of pages) {
            await page.goto(url);
            await page.waitForLoadState('domcontentloaded');
            const overflow = await page.evaluate(() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            });
            expect(overflow, `Horizontal overflow on ${url}`).toBe(false);
        }
    });
});
