'use client';

import { RouteError } from '@/components/RouteError';

export default function ContactError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en contacto', message: 'No se pudo cargar la página de contacto. Intenta de nuevo.' },
        en: { title: 'Contact error', message: 'Could not load the contact page. Please try again.' },
        nah: { title: 'Tlahtlacōlli tēnōnōtzaliztli', message: 'Ahmo huelītic in tēnōnōtzaliztli.' },
      }}
      fallbackHref="/contribuir"
      fallbackLabel={{ es: 'Volver a contribuir', en: 'Back to contribute', nah: 'Xicmocuepa tēpalēhuiliztli' }}
    />
  );
}
