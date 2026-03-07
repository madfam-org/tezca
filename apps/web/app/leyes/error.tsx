'use client';

import { RouteError } from '@/components/RouteError';

export default function LawsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar las leyes', message: 'No se pudieron cargar las leyes. Intenta de nuevo.' },
        en: { title: 'Error loading laws', message: 'Could not load the laws. Please try again.' },
        nah: { title: 'Tlahtlacolli tenahuatilli', message: 'Ahmo hueliz motequihua tenahuatilli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
