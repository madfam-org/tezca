'use client';

import { RouteError } from '@/components/RouteError';

export default function CategoryError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar la categoria', message: 'No se pudo cargar esta categoria. Intenta de nuevo.' },
        en: { title: 'Error loading category', message: 'Could not load this category. Please try again.' },
        nah: { title: 'Tlahtlacolli tlapepenilistli', message: 'Ahmo hueliz motequihua tlapepenilistli.' },
      }}
      fallbackHref="/categorias"
      fallbackLabel={{ es: 'Ver categorias', en: 'View categories', nah: 'Xiquitta tlapepenilistli' }}
    />
  );
}
