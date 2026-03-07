export default function CategoriasLoading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-muted rounded mb-2 animate-pulse" />
        <div className="h-5 w-80 bg-muted/60 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="rounded-xl border bg-card p-6 animate-pulse">
              <div className="h-6 w-3/4 bg-muted rounded mb-3" />
              <div className="h-4 w-1/2 bg-muted/60 rounded mb-2" />
              <div className="h-4 w-1/3 bg-muted/40 rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
