'use client';

import { RouteError } from '@/components/RouteError';

export default function SubmitDataError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al enviar datos', message: 'No se pudo cargar el formulario de envío. Intenta de nuevo.' },
        en: { title: 'Submit data error', message: 'Could not load the submission form. Please try again.' },
        nah: { title: 'Tlahtlacōlli tlatitlaniliztli', message: 'Ahmo huelītic in tlatitlaniliztli.' },
      }}
      fallbackHref="/contribuir"
      fallbackLabel={{ es: 'Volver a contribuir', en: 'Back to contribute', nah: 'Xicmocuepa tēpalēhuiliztli' }}
    />
  );
}
