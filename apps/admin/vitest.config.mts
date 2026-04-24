import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./vitest.setup.ts'],
        exclude: ['node_modules/**'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
        },
        alias: {
            '@': path.resolve(__dirname, './'),
            '@tezca/ui': path.resolve(__dirname, '../../packages/ui/src'),
            '@tezca/lib': path.resolve(__dirname, '../../packages/lib/src'),
            // Vitest's ESM resolver is stricter than Next's build-time bundler.
            // @janua/nextjs/dist/middleware.mjs does `from "next/server"` (bare),
            // which vite-node can't resolve because next has no "exports" field
            // mapping. Force the explicit .js path so the hoisted next package
            // at the root node_modules resolves.
            // TODO: Remove once @janua/nextjs ships with `from "next/server.js"`.
            'next/server': path.resolve(__dirname, '../../node_modules/next/server.js'),
        },
    },
});
