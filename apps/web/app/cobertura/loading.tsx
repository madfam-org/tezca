export default function CoberturaLoading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-muted rounded mb-2 animate-pulse" />
        <div className="h-5 w-72 bg-muted/60 rounded mb-8 animate-pulse" />
        {/* Stat cards skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border bg-card p-6 animate-pulse">
              <div className="h-4 w-20 bg-muted/60 rounded mb-3" />
              <div className="h-8 w-16 bg-muted rounded" />
            </div>
          ))}
        </div>
        {/* Chart/table skeleton */}
        <div className="rounded-xl border bg-card p-6 animate-pulse">
          <div className="h-6 w-40 bg-muted rounded mb-4" />
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="h-4 w-32 bg-muted/60 rounded" />
                <div className="flex-1 h-4 bg-muted/30 rounded" />
                <div className="h-4 w-12 bg-muted/60 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
