'use client';

import { RouteError } from '@/components/RouteError';

export default function FavoritosError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar favoritos', message: 'No se pudieron cargar tus favoritos. Intenta de nuevo.' },
        en: { title: 'Error loading favorites', message: 'Could not load your favorites. Please try again.' },
        nah: { title: 'Tlahtlacolli tlatlazohtlaliztli', message: 'Ahmo hueliz motequihua tlatlazohtlaliztli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
