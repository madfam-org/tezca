export default function LawDetailLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header skeleton */}
      <div className="border-b border-border bg-card">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6">
          <div className="h-4 w-24 bg-muted rounded mb-3 animate-pulse" />
          <div className="h-8 w-96 bg-muted rounded mb-2 animate-pulse" />
          <div className="flex gap-2 mt-3">
            <div className="h-5 w-16 bg-muted rounded animate-pulse" />
            <div className="h-5 w-20 bg-muted rounded animate-pulse" />
          </div>
        </div>
      </div>

      {/* Content skeleton */}
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6">
        <div className="flex gap-8">
          {/* TOC sidebar skeleton */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="sticky top-24 space-y-2">
              <div className="h-5 w-40 bg-muted rounded mb-4 animate-pulse" />
              {[75, 90, 65, 85, 70, 95, 80, 60].map((w, i) => (
                <div key={i} className="h-4 bg-muted rounded animate-pulse" style={{ width: `${w}%` }} />
              ))}
            </div>
          </aside>

          {/* Articles skeleton */}
          <main className="flex-1 space-y-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-lg border bg-card p-6 animate-pulse">
                <div className="h-6 w-32 bg-muted rounded mb-4" />
                <div className="space-y-2">
                  <div className="h-4 w-full bg-muted rounded" />
                  <div className="h-4 w-full bg-muted rounded" />
                  <div className="h-4 w-3/4 bg-muted rounded" />
                  <div className="h-4 w-5/6 bg-muted rounded" />
                </div>
              </div>
            ))}
          </main>
        </div>
      </div>
    </div>
  );
}
