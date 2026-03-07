'use client';

import { RouteError } from '@/components/RouteError';

export default function CompararError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al comparar leyes', message: 'No se pudo completar la comparacion. Intenta de nuevo.' },
        en: { title: 'Error comparing laws', message: 'Could not complete the comparison. Please try again.' },
        nah: { title: 'Tlahtlacolli tlanenehuiliztli', message: 'Ahmo hueliz motequihua tlanenehuiliztli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
