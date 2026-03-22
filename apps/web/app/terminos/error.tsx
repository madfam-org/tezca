'use client';

import { RouteError } from '@/components/RouteError';

export default function TermsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en la página', message: 'No se pudo cargar los términos de uso. Intenta de nuevo.' },
        en: { title: 'Page error', message: 'Could not load the terms of use. Please try again.' },
        nah: { title: 'Tlahtlacōlli āmoxihuitl', message: 'Ahmo huelītic in tlamantli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Xicmocuepa caltenco' }}
    />
  );
}
