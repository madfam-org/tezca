'use client';

import { RouteError } from '@/components/RouteError';

export default function GraphError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en el grafo', message: 'No se pudo cargar el grafo. Intenta de nuevo.' },
        en: { title: 'Graph error', message: 'Could not load the graph. Please try again.' },
        nah: { title: 'Tlahtlacolli in grafo', message: 'Ahmo hueliz motemoa in grafo.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
