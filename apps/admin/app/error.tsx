'use client';

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <h2 className="mb-2 text-xl font-semibold text-foreground">Error</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Ocurrio un error. Intenta de nuevo.
      </p>
      {error?.digest && (
        <p className="mb-4 text-xs text-muted-foreground font-mono">{error.digest}</p>
      )}
      <button
        onClick={reset}
        className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
      >
        Reintentar
      </button>
    </div>
  );
}
