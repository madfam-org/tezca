export default function CategoryLoading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-56 bg-muted rounded mb-2 animate-pulse" />
        <div className="h-5 w-72 bg-muted/60 rounded mb-8 animate-pulse" />
        <div className="space-y-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="rounded-lg border bg-card p-5 animate-pulse">
              <div className="h-5 w-2/3 bg-muted rounded mb-2" />
              <div className="flex gap-2 mb-2">
                <div className="h-4 w-16 bg-muted/60 rounded" />
                <div className="h-4 w-20 bg-muted/60 rounded" />
              </div>
              <div className="h-4 w-1/3 bg-muted/40 rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
