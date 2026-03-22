'use client';

import { RouteError } from '@/components/RouteError';

export default function PricingError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error en precios', message: 'No se pudo cargar los precios. Intenta de nuevo.' },
        en: { title: 'Pricing error', message: 'Could not load the pricing page. Please try again.' },
        nah: { title: 'Tlahtlacolli tlaxtlahuilli', message: 'Ahmo hueliz motemoa tlaxtlahuilli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
