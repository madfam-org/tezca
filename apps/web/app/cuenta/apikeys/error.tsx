'use client';

import { RouteError } from '@/components/RouteError';

export default function ApiKeysError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en llaves de API', message: 'No se pudieron cargar las llaves de API. Intenta de nuevo.' },
        en: { title: 'API keys error', message: 'Could not load API keys. Please try again.' },
        nah: { title: 'Tlahtlacōlli API tlaneltōquiliztli', message: 'Ahmo huelītic in tlaneltōquiliztli.' },
      }}
      fallbackHref="/cuenta"
      fallbackLabel={{ es: 'Volver a mi cuenta', en: 'Back to account', nah: 'Xicmocuepa mocuenta' }}
    />
  );
}
