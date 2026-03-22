'use client';

import { RouteError } from '@/components/RouteError';

export default function LoginError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <RouteError
      error={error}
      reset={reset}
      messages={{
        es: { title: 'Error de inicio de sesión', message: 'No se pudo cargar la página de inicio de sesión. Intenta de nuevo.' },
        en: { title: 'Login error', message: 'Could not load the login page. Please try again.' },
        nah: { title: 'Tlahtlacolli calaquiliztli', message: 'Ahmo hueliz motemoa in calaquiliztli.' },
      }}
      fallbackHref="/leyes"
      fallbackLabel={{ es: 'Ver leyes', en: 'Browse laws', nah: 'Xiquitta tenahuatilli' }}
    />
  );
}
