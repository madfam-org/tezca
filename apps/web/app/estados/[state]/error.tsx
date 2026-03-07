'use client';

import { RouteError } from '@/components/RouteError';

export default function StateError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar el estado', message: 'No se pudo cargar la informacion de este estado. Intenta de nuevo.' },
        en: { title: 'Error loading state', message: 'Could not load this state. Please try again.' },
        nah: { title: 'Tlahtlacolli tlatocayotl', message: 'Ahmo hueliz motequihua tlatocayotl.' },
      }}
      fallbackHref="/estados"
      fallbackLabel={{ es: 'Ver estados', en: 'View states', nah: 'Xiquitta tlatocayotl' }}
    />
  );
}
