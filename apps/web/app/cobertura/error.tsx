'use client';

import { RouteError } from '@/components/RouteError';

export default function CoberturaError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar cobertura', message: 'No se pudo cargar la informacion de cobertura. Intenta de nuevo.' },
        en: { title: 'Error loading coverage', message: 'Could not load coverage data. Please try again.' },
        nah: { title: 'Tlahtlacolli tlanextiliztli', message: 'Ahmo hueliz motequihua tlanextiliztli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
