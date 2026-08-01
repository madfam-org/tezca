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

        // Page should not have horizontal overflow. On failure, name the
        // offending elements — a bare boolean cost multiple blind CI cycles
        // when this fired only in the Linux-runner environment.
        const overflow = await page.evaluate(() => {
            const d = document.documentElement;
            const vw = d.clientWidth;
            const offenders: string[] = [];
            if (d.scrollWidth > vw) {
                document.querySelectorAll('body *').forEach((el) => {
                    const r = el.getBoundingClientRect();
                    if ((r.right > vw + 1 || r.left < -1) && r.width > 0 && offenders.length < 8) {
                        offenders.push(
                            `<${el.tagName.toLowerCase()} class="${String(el.className).slice(0, 80)}"> ` +
                            `left=${Math.round(r.left)} right=${Math.round(r.right)} w=${Math.round(r.width)} ` +
                            `text="${(el.textContent || '').trim().slice(0, 40)}"`
                        );
                    }
                });
            }
            return { scrollWidth: d.scrollWidth, clientWidth: vw, offenders };
        });
        expect(
            overflow.scrollWidth > overflow.clientWidth,
            `Horizontal overflow on /busqueda (scrollWidth=${overflow.scrollWidth} > clientWidth=${overflow.clientWidth}). Offenders:\n${overflow.offenders.join('\n')}`
        ).toBe(false);
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
            // domcontentloaded fires before client components finish their
            // first data fetch/hydration pass (stats grid, ecosystem
            // marquee, disclaimer banner). Measuring scrollWidth against
            // that in-flight skeleton/loading state is racy — wait for the
            // network to go idle so layout has settled to its final shape.
            await page.waitForLoadState('networkidle');
            // On failure, name the offenders — see the /busqueda test above.
            const overflow = await page.evaluate(() => {
                const d = document.documentElement;
                const vw = d.clientWidth;
                const offenders: string[] = [];
                if (d.scrollWidth > vw) {
                    document.querySelectorAll('body *').forEach((el) => {
                        const r = el.getBoundingClientRect();
                        if ((r.right > vw + 1 || r.left < -1) && r.width > 0 && offenders.length < 8) {
                            offenders.push(
                                `<${el.tagName.toLowerCase()} class="${String(el.className).slice(0, 80)}"> ` +
                                `left=${Math.round(r.left)} right=${Math.round(r.right)} w=${Math.round(r.width)} ` +
                                `text="${(el.textContent || '').trim().slice(0, 40)}"`
                            );
                        }
                    });
                }
                return { scrollWidth: d.scrollWidth, clientWidth: vw, offenders };
            });
            expect(
                overflow.scrollWidth > overflow.clientWidth,
                `Horizontal overflow on ${url} (scrollWidth=${overflow.scrollWidth} > clientWidth=${overflow.clientWidth}). Offenders:\n${overflow.offenders.join('\n')}`
            ).toBe(false);
        }
    });
});
