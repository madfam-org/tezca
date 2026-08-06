import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';
import { createRequire } from 'module';

const requireFromHere = createRequire(import.meta.url);

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
            // mapping. Force the explicit .js paths, resolved through Node's
            // own algorithm so they work whether npm hoists next to the root
            // (aligned peers, 2026-08-01 refresh) or nests it per-workspace
            // (the 16.2.10-era conflicted tree) — a hardcoded path broke each
            // time the layout flipped.
            // TODO: Remove once @janua/nextjs ships with `from "next/server.js"`.
            'next/server': requireFromHere.resolve('next/server.js'),
            'next/headers': requireFromHere.resolve('next/headers.js'),
            // Two jose copies exist (admin's own v6 vs the root v5 that the
            // inlined @janua/nextjs resolves). vi.mock('jose') keys on the
            // test file's resolution, so unify both onto one copy or the
            // middleware's verify escapes the mock.
            jose: path.resolve(__dirname, '../../node_modules/jose'),
        },
        server: {
            deps: {
                // vitest v4 stopped applying test.alias inside externalized
                // node_modules imports — inline @janua/nextjs so its bare
                // `from "next/server"` goes through the transform where the
                // alias above still applies.
                inline: ['@janua/nextjs'],
            },
        },
    },
});
