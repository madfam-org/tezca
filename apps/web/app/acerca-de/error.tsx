'use client';

import { RouteError } from '@/components/RouteError';

export default function AboutError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en la página', message: 'No se pudo cargar esta página. Intenta de nuevo.' },
        en: { title: 'Page error', message: 'Could not load this page. Please try again.' },
        nah: { title: 'Tlahtlacōlli āmoxihuitl', message: 'Ahmo huelītic inīn āmoxihuitl.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Xicmocuepa caltenco' }}
    />
  );
}
