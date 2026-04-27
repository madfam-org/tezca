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
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            // `all: true` widens the denominator to every source file under
            // the project, not just files imported by tests. Thresholds are
            // pinned to the observed floor minus ~5pp so unrelated PRs don't
            // trip the gate; ratchet up as component coverage grows.
            // Observed floor (2026-04-27, all:true with full include scope):
            // stmts 56.44, branches 49.68, funcs 52.09, lines 57.66.
            all: true,
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
                statements: 51,
                branches: 44,
                functions: 47,
                lines: 52,
            },
        },
        alias: {
            '@': path.resolve(__dirname, './'),
        },
    },
});
