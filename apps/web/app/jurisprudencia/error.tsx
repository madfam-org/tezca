'use client';

import { RouteError } from '@/components/RouteError';

export default function JurisprudenciaError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar jurisprudencia', message: 'No se pudo cargar la jurisprudencia. Intenta de nuevo.' },
        en: { title: 'Error loading case law', message: 'Could not load case law. Please try again.' },
        nah: { title: 'Tlahtlacolli tlanahuatilmachiyotl', message: 'Ahmo hueliz motequihua tlanahuatilmachiyotl.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
