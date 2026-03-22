'use client';

import { RouteError } from '@/components/RouteError';

export default function AlertsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en alertas', message: 'No se pudieron cargar las alertas. Intenta de nuevo.' },
        en: { title: 'Alerts error', message: 'Could not load alerts. Please try again.' },
        nah: { title: 'Tlahtlacōlli tlanōnōtzaliztli', message: 'Ahmo huelītic in tlanōnōtzaliztli.' },
      }}
      fallbackHref="/cuenta"
      fallbackLabel={{ es: 'Volver a mi cuenta', en: 'Back to account', nah: 'Xicmocuepa mocuenta' }}
    />
  );
}
