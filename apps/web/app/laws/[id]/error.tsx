'use client';

import Link from 'next/link';

export default function LawDetailError({
  error: _error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <h2 className="mb-2 text-xl font-semibold text-foreground">
        Error al cargar la ley
      </h2>
      <p className="mb-6 text-sm text-muted-foreground max-w-md">
        No se pudo cargar el contenido de esta ley. Puede que el servicio esté temporalmente fuera de línea.
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          Reintentar
        </button>
        <Link
          href="/laws"
          className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
        >
          Ver todas las leyes
        </Link>
      </div>
    </div>
  );
}
