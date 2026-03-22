'use client';

import { RouteError } from '@/components/RouteError';

export default function PrivacyError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en la página', message: 'No se pudo cargar la política de privacidad. Intenta de nuevo.' },
        en: { title: 'Page error', message: 'Could not load the privacy policy. Please try again.' },
        nah: { title: 'Tlahtlacōlli āmoxihuitl', message: 'Ahmo huelītic in ichtacayotl.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Xicmocuepa caltenco' }}
    />
  );
}
