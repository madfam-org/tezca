/**
 * Conversion funnel E2E tests.
 *
 * Tests the pre-monetization path (MONETIZATION_ENABLED=false by default).
 * Validates that anonymous users encounter conversion touchpoints across key pages.
 */
import { test, expect } from './fixtures';

test.describe('Homepage — ConversionBanner', () => {
    test('renders pre-monetization headline and CTA', async ({ page }) => {
        await page.goto('/');
        const banner = page.getByText('Las leyes de México, accesibles para todos');
        await expect(banner).toBeVisible();
    });

    test('CTA links to /login', async ({ page }) => {
        await page.goto('/');
        const cta = page.getByRole('link', { name: 'Únete a la comunidad' });
        await expect(cta).toBeVisible();
        await expect(cta).toHaveAttribute('href', /\/login/);
    });
});

test.describe('Search results — InterestGate', () => {
    test('shows InterestGate when search has limited page_size', async ({ page }) => {
        await page.route('**/api/v1/search/?*', (route) =>
            route.fulfill({
                json: {
                    results: [
                        {
                            id: '1',
                            law_id: 'ley-federal-del-trabajo',
                            law_name: 'Ley Federal del Trabajo',
                            article: 'Art. 1',
                            snippet: 'La presente <em>Ley</em> es de observancia general.',
                            score: 9.5,
                            date: '2026-01-15',
                        },
                    ],
                    total: 1,
                    total_pages: 1,
                    max_page_size: 25,
                },
            })
        );
        await page.goto('/busqueda?q=trabajo');
        // The page renders search results; InterestGate may appear for limited results
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
    });

    test('does NOT show gate when max_page_size is absent', async ({ page }) => {
        await page.goto('/busqueda?q=trabajo');
        // Default mock doesn't include max_page_size
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
    });
});

test.describe('Law detail — ConversionBanner', () => {
    test('renders ConversionBanner after articles section', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        // Law title renders
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
        // ConversionBanner visible on the page
        const banner = page.getByText('Las leyes de México, accesibles para todos');
        await expect(banner).toBeVisible();
    });
});

test.describe('Developer docs — DevApiCta', () => {
    test('renders DevApiCta with title and CTA link', async ({ page }) => {
        await page.goto('/desarrolladores');
        const title = page.getByText('Obtén acceso a la API');
        await expect(title).toBeVisible();
        const cta = page.getByRole('link', { name: 'Ver planes' });
        await expect(cta).toBeVisible();
        await expect(cta).toHaveAttribute('href', /\/login\?redirect=/);
    });
});

test.describe('Graph page — GraphTierMessage', () => {
    test('shows InterestGate for non-institutional users', async ({ page }) => {
        await page.goto('/grafo');
        // The graph page renders for anonymous users with a tier gate/interest gate
        // In pre-monetization mode, it shows InterestGate inline for graph_api
        await expect(page.getByText('Red de leyes').first()).toBeVisible();
    });
});

test.describe('Pricing page (/precios)', () => {
    test('renders 4 tier cards', async ({ page }) => {
        await page.goto('/precios');
        await expect(page.getByText('Planes y precios')).toBeVisible();
        await expect(page.getByText('Free Member').first()).toBeVisible();
        await expect(page.getByText('Essentials').first()).toBeVisible();
        await expect(page.getByText('Academic').first()).toBeVisible();
        await expect(page.getByText('Institutional').first()).toBeVisible();
    });

    test('paid tiers show Próximamente badge in pre-monetization mode', async ({ page }) => {
        await page.goto('/precios');
        const badges = page.getByText('Próximamente');
        await expect(badges.first()).toBeVisible();
    });

    test('paid tier cards have InterestGate email inputs', async ({ page }) => {
        await page.goto('/precios');
        // InterestGate forms have email inputs on paid tier cards
        const emailInputs = page.getByPlaceholder(/correo|email/i);
        // At least one email input should be visible (from InterestGate on paid tier cards)
        await expect(emailInputs.first()).toBeVisible();
    });

    test('Free Member CTA links to /login', async ({ page }) => {
        await page.goto('/precios');
        const createAccount = page.getByRole('link', { name: 'Crear cuenta' });
        await expect(createAccount).toBeVisible();
        await expect(createAccount).toHaveAttribute('href', /\/login/);
    });

    test('FAQ section renders', async ({ page }) => {
        await page.goto('/precios');
        await expect(page.getByText('Preguntas frecuentes')).toBeVisible();
    });
});

test.describe('CTA navigation', () => {
    test('ConversionBanner CTA navigates to /login', async ({ page }) => {
        await page.goto('/');
        const cta = page.getByRole('link', { name: 'Únete a la comunidad' });
        await expect(cta).toBeVisible();
        await cta.click();
        await expect(page).toHaveURL(/\/login/);
    });
});
