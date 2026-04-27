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
            // NOTE: thresholds below cover only files imported by tests
            // (the v8 default). Switching to `all: true` would widen the
            // denominator across the whole project — currently ~15% of
            // components have unit tests so the gate would instantly fail.
            // Plan: backfill component tests, then flip `all: true` and
            // ratchet these numbers up. Tracked as a follow-up.
            thresholds: {
                statements: 70,
                branches: 60,
                functions: 70,
                lines: 70,
            },
        },
        alias: {
            '@': path.resolve(__dirname, './'),
        },
    },
});
