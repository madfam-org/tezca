import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const PAGES_TO_AUDIT = [
    { url: '/', name: 'Homepage' },
    { url: '/busqueda', name: 'Search' },
    { url: '/leyes', name: 'Law Catalog' },
    { url: '/categorias', name: 'Categories' },
    { url: '/estados', name: 'States' },
    { url: '/comparar', name: 'Compare' },
];

test.describe('Accessibility (WCAG 2.1 AA)', () => {
    for (const { url, name } of PAGES_TO_AUDIT) {
        test(`${name} (${url}) has no WCAG 2.1 AA violations`, async ({ page }) => {
            await page.goto(url);
            await page.waitForLoadState('domcontentloaded');

            const results = await new AxeBuilder({ page })
                .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
                .exclude('.recharts-wrapper') // Exclude chart SVGs (known complex)
                .analyze();

            const violations = results.violations.map((v) => ({
                id: v.id,
                impact: v.impact,
                description: v.description,
                nodes: v.nodes.length,
                help: v.helpUrl,
            }));

            if (violations.length > 0) {
                console.log(`\nA11y violations on ${name} (${url}):`);
                for (const v of violations) {
                    console.log(`  [${v.impact}] ${v.id}: ${v.description} (${v.nodes} nodes)`);
                    console.log(`    ${v.help}`);
                }
            }

            expect(
                violations.filter((v) => v.impact === 'critical' || v.impact === 'serious'),
                `Critical/serious a11y violations on ${name}`,
            ).toHaveLength(0);
        });
    }
});
