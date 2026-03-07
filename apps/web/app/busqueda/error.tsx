'use client';

import { RouteError } from '@/components/RouteError';

export default function SearchError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en la busqueda', message: 'No se pudo completar la busqueda. Intenta de nuevo.' },
        en: { title: 'Search error', message: 'Could not complete the search. Please try again.' },
        nah: { title: 'Tlahtlacolli tlatemoliztli', message: 'Ahmo hueliz motequihua tlatemoliztli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
