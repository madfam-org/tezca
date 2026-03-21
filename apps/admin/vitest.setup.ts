import '@testing-library/jest-dom';

// jsdom does not implement ResizeObserver. Polyfill it so Radix UI
// components (which observe container sizes) can render in tests.
if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}
