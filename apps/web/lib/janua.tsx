'use client';

import { type ComponentProps, useMemo } from 'react';
import { JanuaProvider as BaseJanuaProvider } from '@janua/nextjs';
import { serverSafeJanuaConfig } from './janua-config';

type JanuaProviderProps = ComponentProps<typeof BaseJanuaProvider>;

/**
 * App-wide `<JanuaProvider>`. The root layout is a server component, so the
 * server/browser decision has to happen here, at render time in this client
 * module: on the server the client is built with `autoRefreshTokens: false`
 * (see `lib/janua-config.ts` — the SDK leaked one interval per server render),
 * in the browser the config passes through unchanged.
 */
export function JanuaProvider({ config, ...rest }: JanuaProviderProps) {
  const effectiveConfig = useMemo(() => serverSafeJanuaConfig(config), [config]);
  return <BaseJanuaProvider {...rest} config={effectiveConfig} />;
}
