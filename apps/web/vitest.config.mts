import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@janua/nextjs/middleware': path.resolve(__dirname, '__mocks__/@janua/nextjs-middleware.ts'),
            '@janua/nextjs/server': path.resolve(__dirname, '__mocks__/@janua/nextjs-server.ts'),
            '@janua/nextjs': path.resolve(__dirname, '__mocks__/@janua/nextjs.ts'),
        },
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./vitest.setup.ts'],
        exclude: ['e2e/**', 'node_modules/**'],
        server: {
            deps: {
                // `@janua/nextjs` itself is aliased to a stub above, but the
                // provider SSR regression test loads the REAL package by file
                // path (`__tests__/lib/janua-provider-ssr.test.tsx`). Its ESM
                // dist imports `next/headers` without an extension, which
                // Node's ESM loader rejects; inlining lets Vite resolve it.
                inline: [/@janua\/nextjs\/dist\//],
            },
        },
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            // `all: true` widens the denominator to every source file under
            // the project, not just files imported by tests.
            //
            // WS-R2 (2026-04-27): floor pushed via 12 new test files (api.ts
            // facade, graph components, skeletons, JsonLd, AnnotationBadge,
            // MetricCard, LawArticles, StatesGrid, theme-provider, etc.).
            //   Observed floor: stmts 63.33, branches 56.82, funcs 60.19, lines 64.18.
            //   Gates pinned at floor−2pp for headroom against minor drift.
            //
            // WS2 Phase 2C lock target ≥50/40/50/50 — well exceeded.
            //
            // (vitest v4 removed `all: true` — files matching `include` are
            // now always counted, untested or not, so the gate semantics
            // are unchanged.)
            include: ['app/**', 'components/**', 'hooks/**', 'lib/**', 'contexts/**'],
            exclude: [
                '**/*.d.ts',
                '**/*.config.*',
                '**/node_modules/**',
                '**/.next/**',
                '**/__tests__/**',
                '**/__mocks__/**',
                'e2e/**',
            ],
            thresholds: {
                statements: 61,
                branches: 54,
                functions: 58,
                lines: 62,
            },
        },
        alias: {
            '@': path.resolve(__dirname, './'),
        },
    },
});
