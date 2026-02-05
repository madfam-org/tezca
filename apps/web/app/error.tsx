'use client';

import Link from 'next/link';

export default function Error({
  error: _error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8 text-center bg-background">
      <h2 className="mb-2 text-2xl font-semibold text-foreground">
        Algo salió mal
      </h2>
      <p className="mb-6 text-sm text-muted-foreground max-w-md">
        Ocurrió un error inesperado. Puedes intentar recargar la página o volver al inicio.
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          Reintentar
        </button>
        <Link
          href="/"
          className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
        >
          Ir al inicio
        </Link>
      </div>
    </div>
  );
}
