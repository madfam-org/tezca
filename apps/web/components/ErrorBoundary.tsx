'use client';

import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

function getPreferredLang(): 'es' | 'en' | 'nah' {
  if (typeof window === 'undefined') return 'es';
  try {
    const stored = localStorage.getItem('preferred-lang');
    if (stored === 'en' || stored === 'nah') return stored;
    return 'es';
  } catch {
    return 'es';
  }
}

const content = {
  es: {
    title: 'Algo salió mal',
    message: 'Ocurrió un error inesperado. Intenta recargar la página.',
    retry: 'Reintentar',
  },
  en: {
    title: 'Something went wrong',
    message: 'An unexpected error occurred. Try reloading the page.',
    retry: 'Retry',
  },
  nah: {
    title: 'Itlah ahmo cualli ōmochiuh',
    message: 'Ahmo tēmachīlli tlahtlacōlli ōmochiuh. Xicyancuīlia in āmatl.',
    retry: 'Xicyancuīlia',
  },
};

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    import('@/lib/sentry').then(({ captureError }) => {
      captureError(error, { componentStack: errorInfo.componentStack });
    });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const t = content[getPreferredLang()];

      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center p-8 text-center">
          <h2 className="mb-2 text-xl font-semibold text-foreground">
            {t.title}
          </h2>
          <p className="mb-4 text-sm text-muted-foreground">
            {t.message}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          >
            {t.retry}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
