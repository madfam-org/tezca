'use client';

import { RouteError } from '@/components/RouteError';

export default function LegalNoticeError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en la página', message: 'No se pudo cargar el aviso legal. Intenta de nuevo.' },
        en: { title: 'Page error', message: 'Could not load the legal notice. Please try again.' },
        nah: { title: 'Tlahtlacōlli āmoxihuitl', message: 'Ahmo huelītic in tenahuatilli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Xicmocuepa caltenco' }}
    />
  );
}
