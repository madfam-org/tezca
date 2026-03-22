'use client';

import { RouteError } from '@/components/RouteError';

export default function CallForDataError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en convocatoria', message: 'No se pudo cargar la convocatoria. Intenta de nuevo.' },
        en: { title: 'Call for data error', message: 'Could not load the call for data page. Please try again.' },
        nah: { title: 'Tlahtlacolli tlanonotzaliztli', message: 'Ahmo hueliz motemoa tlanonotzaliztli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
