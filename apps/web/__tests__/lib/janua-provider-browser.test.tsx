import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const baseProvider = vi.hoisted(() =>
  vi.fn(({ children }: { children: React.ReactNode; config: unknown }) => <>{children}</>),
);
vi.mock('@janua/nextjs', () => ({ JanuaProvider: baseProvider }));

import { JanuaProvider } from '@/lib/janua';

const LAYOUT_CONFIG = { baseURL: 'https://auth.example.test', apiKey: 'pk_test_synthetic' };

// jsdom: `window` exists, so this is the browser path. The browser must keep
// exactly today's config so signed-in sessions keep refreshing their tokens.
describe('JanuaProvider in the browser', () => {
  afterEach(() => {
    baseProvider.mockClear();
  });

  it('passes the layout config through unchanged (same object, no autoRefreshTokens key)', () => {
    const { getByText } = render(
      <JanuaProvider config={LAYOUT_CONFIG}>
        <p>child</p>
      </JanuaProvider>,
    );
    expect(getByText('child')).toBeInTheDocument();
    const passed = baseProvider.mock.calls[0][0].config;
    expect(passed).toBe(LAYOUT_CONFIG);
    expect('autoRefreshTokens' in (passed as object)).toBe(false);
  });

  it('keeps the config identity stable across re-renders', () => {
    const { rerender } = render(
      <JanuaProvider config={LAYOUT_CONFIG}>
        <p>a</p>
      </JanuaProvider>,
    );
    rerender(
      <JanuaProvider config={LAYOUT_CONFIG}>
        <p>b</p>
      </JanuaProvider>,
    );
    const configs = baseProvider.mock.calls.map(([props]) => props.config);
    expect(configs.length).toBeGreaterThanOrEqual(2);
    for (const c of configs) expect(c).toBe(LAYOUT_CONFIG);
  });

  it('forwards onAuthChange to the base provider', () => {
    const onAuthChange = vi.fn();
    render(
      <JanuaProvider config={LAYOUT_CONFIG} onAuthChange={onAuthChange}>
        <p>child</p>
      </JanuaProvider>,
    );
    expect(baseProvider.mock.calls[0][0]).toMatchObject({ onAuthChange });
  });
});
