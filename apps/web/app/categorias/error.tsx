'use client';

import { RouteError } from '@/components/RouteError';

export default function CategoriasError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar categorias', message: 'No se pudieron cargar las categorias. Intenta de nuevo.' },
        en: { title: 'Error loading categories', message: 'Could not load categories. Please try again.' },
        nah: { title: 'Tlahtlacolli tlapepenilistli', message: 'Ahmo hueliz motequihua tlapepenilistli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
