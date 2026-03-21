import '@testing-library/jest-dom';

// Polyfill APIs missing in jsdom
if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class ResizeObserver {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof globalThis.ResizeObserver;
}
