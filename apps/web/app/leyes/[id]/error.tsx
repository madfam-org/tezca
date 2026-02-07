'use client';

import Link from 'next/link';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Error al cargar la ley',
        message: 'No se pudo cargar el contenido de esta ley. Puede que el servicio esté temporalmente fuera de línea.',
        retry: 'Reintentar',
        viewAll: 'Ver todas las leyes',
    },
    en: {
        title: 'Error loading law',
        message: 'Could not load the content of this law. The service may be temporarily unavailable.',
        retry: 'Retry',
        viewAll: 'View all laws',
    },
    nah: {
        title: 'Tlahtlacōlli ic motēmoa tenahuatilli',
        message: 'Ahmo huelīz motēmoa in tenahuatilli. Huelīz in tēquitiliztli ahmo āxcān.',
        retry: 'Occēppa',
        viewAll: 'Xiquitta mochi tenahuatilli',
    },
};

export default function LawDetailError({
  error: _error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { lang } = useLang();
  const t = content[lang];

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <h2 className="mb-2 text-xl font-semibold text-foreground">
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
          href="/leyes"
          className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
        >
          {t.viewAll}
        </Link>
      </div>
    </div>
  );
}
