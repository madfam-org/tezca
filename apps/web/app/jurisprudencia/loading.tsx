export default function JurisprudenciaLoading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-52 bg-muted rounded mb-2 animate-pulse" />
        <div className="h-5 w-80 bg-muted/60 rounded mb-8 animate-pulse" />
        <div className="flex gap-8">
          {/* Filter skeleton */}
          <aside className="hidden lg:block w-64 flex-shrink-0 space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 w-24 bg-muted rounded mb-2" />
                <div className="h-9 w-full bg-muted rounded" />
              </div>
            ))}
          </aside>
          {/* Results skeleton */}
          <main className="flex-1 space-y-4">
            <div className="h-4 w-32 bg-muted rounded mb-4 animate-pulse" />
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-lg border bg-card p-5 animate-pulse">
                <div className="h-5 w-3/4 bg-muted rounded mb-2" />
                <div className="h-4 w-full bg-muted/60 rounded mb-1" />
                <div className="h-4 w-5/6 bg-muted/60 rounded mb-2" />
                <div className="h-3 w-1/4 bg-muted/40 rounded" />
              </div>
            ))}
          </main>
        </div>
      </div>
    </div>
  );
}
