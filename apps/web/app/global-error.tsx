'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    import('@/lib/sentry').then(({ captureError }) => {
      captureError(error, { digest: error.digest, route: 'global' });
    });
  }, [error]);

  // This component renders outside the theme provider (<html> + <body>
  // without providers), so CSS custom properties like bg-background are
  // undefined. Raw Tailwind color classes are intentional here.
  return (
    <html lang="es">
      <body className="flex min-h-screen items-center justify-center bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-100 p-8">
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-semibold mb-2">Algo salió mal</h2>
          <p className="text-sm text-gray-500 mb-6">
            Ocurrió un error inesperado. Intenta recargar la página.
          </p>
          {error?.digest && (
            <p className="text-xs text-gray-400 font-mono mb-4">{error.digest}</p>
          )}
          <button
            onClick={reset}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Reintentar
          </button>
        </div>
      </body>
    </html>
  );
}
