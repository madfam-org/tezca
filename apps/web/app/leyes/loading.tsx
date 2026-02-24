export default function LawsLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header skeleton */}
      <div className="bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="h-10 w-64 bg-white/20 rounded mb-2 animate-pulse" />
          <div className="h-6 w-96 bg-white/10 rounded animate-pulse" />
        </div>
      </div>

      {/* Stats skeleton */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl p-6 shadow-lg border-l-4 border-muted animate-pulse">
              <div className="h-4 w-24 bg-muted rounded mb-3" />
              <div className="h-8 w-16 bg-muted rounded" />
            </div>
          ))}
        </div>

        {/* Law cards skeleton */}
        <div className="h-7 w-40 bg-muted rounded mb-6 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl p-6 shadow-lg animate-pulse">
              <div className="h-6 w-full bg-muted rounded mb-3" />
              <div className="flex gap-2 mb-4">
                <div className="h-5 w-16 bg-muted rounded" />
                <div className="h-5 w-20 bg-muted rounded" />
              </div>
              <div className="h-4 w-32 bg-muted rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
