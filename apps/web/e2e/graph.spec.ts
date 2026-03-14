import { test, expect, MOCK_LAW_GRAPH, MOCK_GRAPH_OVERVIEW } from './fixtures';

test.describe('Graph overview page (/grafo)', () => {
    test('renders overview title in fullscreen mode', async ({ page }) => {
        await page.goto('/grafo');
        // In fullscreen mode, the page uses LawGraphContainer mode="fullscreen"
        await expect(page.getByText('Red de leyes').first()).toBeVisible();
    });

    test('renders graph canvas container', async ({ page }) => {
        await page.goto('/grafo');
        // Wait for data to load
        await expect(page.locator('section')).toBeVisible();
        // Sigma renders inside the graph container
        const graphContainer = page.locator('[style*="cursor"]');
        await expect(graphContainer.first()).toBeVisible();
    });

    test('renders legend with category labels by default', async ({ page }) => {
        await page.goto('/grafo');
        await expect(page.getByText('Color por:').first()).toBeVisible();
        // Category mode is the default
        await expect(page.getByText('Categoría').first()).toBeVisible();
        await expect(page.getByText('Nivel').first()).toBeVisible();
    });

    test('shows search input in fullscreen mode', async ({ page }) => {
        await page.goto('/grafo');
        await expect(page.getByPlaceholder('Buscar ley...')).toBeVisible();
    });

    test('shows stats panel in fullscreen mode', async ({ page }) => {
        await page.goto('/grafo');
        await expect(page.getByText('Estadísticas')).toBeVisible();
    });

    test('does NOT show controls on overview', async ({ page }) => {
        await page.goto('/grafo');
        // Wait for graph to render
        await expect(page.locator('section')).toBeVisible();
        // No depth/direction/confidence controls on overview
        const section = page.locator('section');
        await expect(section.locator('select')).toHaveCount(0);
        await expect(section.locator('input[type="range"]')).toHaveCount(0);
    });

    test('shows loading state before data arrives', async ({ page }) => {
        // Delay the API response to observe loading indicator
        await page.route(new RegExp('/api/v1/graph/overview/'), async (route) => {
            await new Promise((r) => setTimeout(r, 500));
            await route.fulfill({ json: MOCK_GRAPH_OVERVIEW });
        });
        await page.goto('/grafo');
        await expect(page.getByText('Cargando grafo...')).toBeVisible();
    });

    test('shows error state on API failure', async ({ page }) => {
        await page.route(new RegExp('/api/v1/graph/overview/'), (route) =>
            route.fulfill({ status: 500, json: { detail: 'Server error' } })
        );
        await page.goto('/grafo');
        await expect(page.getByText('No se pudo cargar el grafo')).toBeVisible();
    });

    test('shows empty state when no nodes', async ({ page }) => {
        await page.route(new RegExp('/api/v1/graph/overview/'), (route) =>
            route.fulfill({
                json: {
                    ...MOCK_GRAPH_OVERVIEW,
                    nodes: [],
                    edges: [],
                    meta: { total_nodes: 0, total_edges: 0, depth_reached: 0, truncated: false },
                },
            })
        );
        await page.goto('/grafo');
        await expect(page.getByText('No hay referencias suficientes para visualizar')).toBeVisible();
    });
});

test.describe('Law-specific graph (/leyes/{lawId})', () => {
    test('renders section title', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        await expect(page.getByText('Grafo de referencias').first()).toBeVisible();
    });

    test('renders controls with correct labels', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText('Profundidad:')).toBeVisible();
        await expect(section.getByText('Dirección:')).toBeVisible();
        await expect(section.getByText('Confianza mín.:')).toBeVisible();
    });

    test('shows stats line', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();
        await expect(section.getByText(/2 aristas/)).toBeVisible();
    });

    test('shows truncated indicator', async ({ page }) => {
        await page.route(new RegExp('/api/v1/laws/[^/]+/graph/'), (route) =>
            route.fulfill({
                json: {
                    ...MOCK_LAW_GRAPH,
                    meta: { ...MOCK_LAW_GRAPH.meta, truncated: true },
                },
            })
        );
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText('(truncado)')).toBeVisible();
    });

    test('shows empty state', async ({ page }) => {
        await page.route(new RegExp('/api/v1/laws/[^/]+/graph/'), (route) =>
            route.fulfill({
                json: {
                    ...MOCK_LAW_GRAPH,
                    nodes: [],
                    edges: [],
                    meta: { total_nodes: 0, total_edges: 0, depth_reached: 0, truncated: false },
                },
            })
        );
        await page.goto('/leyes/ley-federal-del-trabajo');
        await expect(page.getByText('No hay referencias suficientes para visualizar')).toBeVisible();
    });

    test('shows error state while law detail still renders', async ({ page }) => {
        await page.route(new RegExp('/api/v1/laws/[^/]+/graph/'), (route) =>
            route.fulfill({ status: 500, json: { detail: 'Server error' } })
        );
        await page.goto('/leyes/ley-federal-del-trabajo');
        // Graph error appears
        await expect(page.getByText('No se pudo cargar el grafo')).toBeVisible();
        // But the law header still renders
        await expect(page.getByText('Ley Federal del Trabajo').first()).toBeVisible();
    });

    test('fullscreen button is present', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();
        await expect(section.getByRole('button', { name: 'Pantalla completa' })).toBeVisible();
    });

    test('export PNG button is present', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();
        await expect(section.getByRole('button', { name: 'Exportar PNG' })).toBeVisible();
    });

    test('reset view button is present', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();
        await expect(section.getByRole('button', { name: 'Restablecer vista' })).toBeVisible();
    });
});

test.describe('Graph controls interaction', () => {
    test('depth select has 3 options', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        const depthSelect = section.locator('select').first();
        await expect(depthSelect).toBeVisible();
        const options = depthSelect.locator('option');
        await expect(options).toHaveCount(3);
        await expect(options.nth(0)).toHaveText('1');
        await expect(options.nth(1)).toHaveText('2');
        await expect(options.nth(2)).toHaveText('3');
    });

    test('direction select has 3 options', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        const directionSelect = section.locator('select').nth(1);
        await expect(directionSelect).toBeVisible();
        const options = directionSelect.locator('option');
        await expect(options).toHaveCount(3);
        await expect(options.nth(0)).toHaveText('Ambas');
        await expect(options.nth(1)).toHaveText('Salientes');
        await expect(options.nth(2)).toHaveText('Entrantes');
    });

    test('confidence slider has correct attributes and shows value', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        const slider = section.locator('input[type="range"]');
        await expect(slider).toBeVisible();
        await expect(slider).toHaveAttribute('min', '0');
        await expect(slider).toHaveAttribute('max', '1');
        await expect(slider).toHaveAttribute('step', '0.1');
        // Default confidence value displayed next to slider
        await expect(section.getByText('0.5')).toBeVisible();
    });

    test('changing depth triggers API call with depth param', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();

        const requestPromise = page.waitForRequest((req) =>
            req.url().includes('/graph/') && req.url().includes('depth=2')
        );
        await section.locator('select').first().selectOption('2');
        await requestPromise;
    });

    test('changing direction triggers API call with direction param', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();

        const requestPromise = page.waitForRequest((req) =>
            req.url().includes('/graph/') && req.url().includes('direction=outgoing')
        );
        await section.locator('select').nth(1).selectOption('outgoing');
        await requestPromise;
    });

    test('changing confidence triggers API call with min_confidence param', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();

        const requestPromise = page.waitForRequest((req) =>
            req.url().includes('/graph/') && req.url().includes('min_confidence=0.9')
        );
        await section.locator('input[type="range"]').fill('0.9');
        await requestPromise;
    });
});

test.describe('Graph navigation integration', () => {
    test('Grafo navbar link navigates to /grafo', async ({ page }) => {
        await page.goto('/');
        const grafoLink = page.getByRole('link', { name: 'Grafo' }).first();
        await expect(grafoLink).toBeVisible();
        await expect(grafoLink).toHaveAttribute('href', '/grafo');
        await grafoLink.click();
        await expect(page).toHaveURL('/grafo');
        await expect(page.getByText('Red de leyes').first()).toBeVisible();
    });

    test('graph section present on law detail page', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section).toBeVisible();
    });
});

test.describe('Graph color mode', () => {
    test('legend shows category/tier toggle', async ({ page }) => {
        await page.goto('/leyes/ley-federal-del-trabajo');
        const section = page.locator('section').filter({ hasText: 'Grafo de referencias' });
        await expect(section.getByText(/3 nodos/)).toBeVisible();
        await expect(section.getByText('Color por:')).toBeVisible();
        await expect(section.getByText('Categoría')).toBeVisible();
        await expect(section.getByText('Nivel')).toBeVisible();
    });
});
