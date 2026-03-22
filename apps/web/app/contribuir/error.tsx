'use client';

import { RouteError } from '@/components/RouteError';

export default function ContributionsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en contribuciones', message: 'No se pudo cargar las contribuciones. Intenta de nuevo.' },
        en: { title: 'Contributions error', message: 'Could not load contributions. Please try again.' },
        nah: { title: 'Tlahtlacolli tlapalēhuiliztli', message: 'Ahmo hueliz motemoa tlapalēhuiliztli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
