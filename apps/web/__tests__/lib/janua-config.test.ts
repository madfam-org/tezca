// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest';
import { JanuaClient } from '@janua/typescript-sdk';
import { serverSafeJanuaConfig } from '@/lib/janua-config';

const SDK_REFRESH_INTERVAL_MS = 60 * 1000;
const CONFIG = { baseURL: 'https://auth.example.test', apiKey: 'pk_test_synthetic' };

function refreshIntervalsStarted(spy: { mock: { calls: ReadonlyArray<ReadonlyArray<unknown>> } }) {
  return spy.mock.calls.filter(([, ms]) => ms === SDK_REFRESH_INTERVAL_MS).length;
}

describe('serverSafeJanuaConfig', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('turns token auto-refresh off on the server', () => {
    expect(serverSafeJanuaConfig(CONFIG, true).autoRefreshTokens).toBe(false);
  });

  it('overrides an explicit autoRefreshTokens: true on the server', () => {
    expect(serverSafeJanuaConfig({ ...CONFIG, autoRefreshTokens: true }, true).autoRefreshTokens).toBe(false);
  });

  it('keeps every other field on the server and does not mutate the input', () => {
    const input = { ...CONFIG };
    const out = serverSafeJanuaConfig(input, true);
    expect(out).toEqual({ ...CONFIG, autoRefreshTokens: false });
    expect('autoRefreshTokens' in input).toBe(false);
  });

  it('returns the browser config untouched (same object, no new key)', () => {
    const input = { ...CONFIG };
    const out = serverSafeJanuaConfig(input, false);
    expect(out).toBe(input);
    expect('autoRefreshTokens' in out).toBe(false);
  });

  it('leaves an explicit browser autoRefreshTokens as the caller set it', () => {
    expect(serverSafeJanuaConfig({ ...CONFIG, autoRefreshTokens: true }, false).autoRefreshTokens).toBe(true);
    expect(serverSafeJanuaConfig({ ...CONFIG, autoRefreshTokens: false }, false).autoRefreshTokens).toBe(false);
  });

  it('detects the server from the absence of window by default', () => {
    // This file runs in the node environment: no window.
    expect(typeof window).toBe('undefined');
    expect(serverSafeJanuaConfig(CONFIG).autoRefreshTokens).toBe(false);
  });

  // Regression for the tezca-web OOM: one JanuaClient is constructed per
  // server render, and each started a 60 s interval that was never cleared.
  it('a JanuaClient built from the server config starts no refresh interval', () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    for (let i = 0; i < 25; i++) new JanuaClient(serverSafeJanuaConfig(CONFIG, true));
    expect(refreshIntervalsStarted(spy)).toBe(0);
  });

  // Characterisation of the upstream SDK behaviour this guard exists for. When
  // @janua/typescript-sdk stops leaking (0.1.5: no interval off-browser), this
  // test fails: bump the SDK, then delete the guard and this file.
  it('the SDK default still starts one never-cleared interval per client', () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    // Stubbed so the test itself leaves no real 60 s timers behind.
    spy.mockImplementation((() => 0) as unknown as typeof setInterval);
    new JanuaClient(CONFIG);
    new JanuaClient(CONFIG);
    expect(refreshIntervalsStarted(spy)).toBe(2);
  });
});
