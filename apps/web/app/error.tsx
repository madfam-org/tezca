'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useLang } from '@/components/providers/LanguageContext';
import { captureError } from '@/lib/sentry';

const content = {
    es: {
        title: 'Algo salió mal',
        message: 'Ocurrió un error inesperado. Puedes intentar recargar la página o volver al inicio.',
        retry: 'Reintentar',
        goHome: 'Ir al inicio',
    },
    en: {
        title: 'Something went wrong',
        message: 'An unexpected error occurred. You can try reloading the page or go back to the homepage.',
        retry: 'Retry',
        goHome: 'Go home',
    },
    nah: {
        title: 'Itlah ahmo cualli ōmochiuh',
        message: 'Ahmo tēmachīlli tlahtlacōlli ōmochiuh. Huelīz xicyancuīlia in āmatl.',
        retry: 'Xicyancuīlia',
        goHome: 'Caltenco',
    },
};

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { lang } = useLang();
  const t = content[lang];

  useEffect(() => {
    captureError(error, { digest: error.digest, route: 'root' });
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8 text-center bg-background">
      <h2 className="mb-2 text-2xl font-semibold text-foreground">
        {t.title}
      </h2>
      <p className="mb-6 text-sm text-muted-foreground max-w-md">
        {t.message}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          {t.retry}
        </button>
        <Link
          href="/"
          className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
        >
          {t.goHome}
        </Link>
      </div>
    </div>
  );
}
