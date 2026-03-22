'use client';

import { RouteError } from '@/components/RouteError';

export default function DevelopersError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en desarrolladores', message: 'No se pudo cargar la página de desarrolladores. Intenta de nuevo.' },
        en: { title: 'Developers error', message: 'Could not load the developers page. Please try again.' },
        nah: { title: 'Tlahtlacolli tlachihualiztli', message: 'Ahmo hueliz motemoa tlachihualiztli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
