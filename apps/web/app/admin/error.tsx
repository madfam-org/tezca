'use client';

import { RouteError } from '@/components/RouteError';

export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error del panel', message: 'No se pudo cargar el panel de administración. Intenta de nuevo.' },
        en: { title: 'Admin panel error', message: 'Could not load the admin panel. Please try again.' },
        nah: { title: 'Tlahtlacōlli tlatocayotl', message: 'Ahmo huelītic in tlatocayotl.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Xicmocuepa caltenco' }}
    />
  );
}
