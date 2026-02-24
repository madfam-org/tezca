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
            thresholds: {
                statements: 60,
                branches: 50,
                functions: 60,
                lines: 60,
            },
        },
        alias: {
            '@': path.resolve(__dirname, './'),
        },
    },
});
