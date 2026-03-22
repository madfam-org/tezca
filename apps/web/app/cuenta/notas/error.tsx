'use client';

import { RouteError } from '@/components/RouteError';

export default function NotesError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en notas', message: 'No se pudieron cargar las notas. Intenta de nuevo.' },
        en: { title: 'Notes error', message: 'Could not load notes. Please try again.' },
        nah: { title: 'Tlahtlacōlli tlahcuilōlli', message: 'Ahmo huelītic in tlahcuilōlli.' },
      }}
      fallbackHref="/cuenta"
      fallbackLabel={{ es: 'Volver a mi cuenta', en: 'Back to account', nah: 'Xicmocuepa mocuenta' }}
    />
  );
}
