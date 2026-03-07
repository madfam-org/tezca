'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useLang } from '@/components/providers/LanguageContext';
import { captureError } from '@/lib/sentry';

type Lang = 'es' | 'en' | 'nah';

interface RouteErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
  messages: Record<Lang, { title: string; message: string }>;
  fallbackHref: string;
  fallbackLabel: Record<Lang, string>;
}

const shared = {
  es: { retry: 'Reintentar' },
  en: { retry: 'Retry' },
  nah: { retry: 'Occeppa' },
};

export function RouteError({ error, reset, messages, fallbackHref, fallbackLabel }: RouteErrorProps) {
  const { lang } = useLang();
  const t = messages[lang];

  useEffect(() => {
    captureError(error, { digest: error.digest });
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <h2 className="mb-2 text-xl font-semibold text-foreground">{t.title}</h2>
      <p className="mb-6 text-sm text-muted-foreground max-w-md">{t.message}</p>
      {error.digest && (
        <p className="mb-4 text-xs text-muted-foreground font-mono">{error.digest}</p>
      )}
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          {shared[lang].retry}
        </button>
        <Link
          href={fallbackHref}
          className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
        >
          {fallbackLabel[lang]}
        </Link>
      </div>
    </div>
  );
}
