'use client';

import { RouteError } from '@/components/RouteError';

export default function CuentaError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error al cargar tu cuenta', message: 'No se pudo cargar la informacion de tu cuenta. Intenta de nuevo.' },
        en: { title: 'Error loading your account', message: 'Could not load your account information. Please try again.' },
        nah: { title: 'Tlahtlacolli motlapohualli', message: 'Ahmo hueliz motequihua motlapohualli.' },
      }}
      fallbackHref="/"
      fallbackLabel={{ es: 'Ir al inicio', en: 'Go home', nah: 'Caltenco' }}
    />
  );
}
