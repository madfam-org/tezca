export default function SearchLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Search header skeleton */}
      <div className="border-b border-border bg-card">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6 sm:py-8">
          <div className="h-8 w-40 bg-muted rounded mb-6 animate-pulse" />
          <div className="flex gap-2">
            <div className="flex-1 h-10 bg-muted rounded animate-pulse" />
            <div className="h-10 w-20 bg-muted rounded animate-pulse" />
          </div>
        </div>
      </div>

      {/* Content skeleton */}
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6 sm:py-8">
        <div className="flex gap-8">
          {/* Filters sidebar skeleton */}
          <aside className="hidden lg:block w-64 flex-shrink-0 space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 w-24 bg-muted rounded mb-2" />
                <div className="h-9 w-full bg-muted rounded" />
              </div>
            ))}
          </aside>

          {/* Results skeleton */}
          <main className="flex-1 space-y-4">
            <div className="h-4 w-40 bg-muted rounded mb-6 animate-pulse" />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="rounded-lg border bg-card p-6 animate-pulse">
                <div className="flex gap-2 mb-2">
                  <div className="h-5 w-32 bg-muted rounded" />
                  <div className="h-5 w-16 bg-muted rounded" />
                </div>
                <div className="space-y-2">
                  <div className="h-4 w-full bg-muted rounded" />
                  <div className="h-4 w-5/6 bg-muted rounded" />
                </div>
                <div className="h-3 w-28 bg-muted rounded mt-3" />
              </div>
            ))}
          </main>
        </div>
      </div>
    </div>
  );
}
