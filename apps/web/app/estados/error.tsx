'use client';

import { RouteError } from '@/components/RouteError';

export default function EstadosError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar estados', message: 'No se pudieron cargar los estados. Intenta de nuevo.' },
        en: { title: 'Error loading states', message: 'Could not load states. Please try again.' },
        nah: { title: 'Tlahtlacolli tlatocayotl', message: 'Ahmo hueliz motequihua tlatocayotl.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
