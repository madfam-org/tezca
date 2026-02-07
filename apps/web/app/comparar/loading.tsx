export default function CompareLoading() {
  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      {/* Header skeleton */}
      <div className="flex items-center gap-4 py-4 px-6 border-b animate-pulse">
        <div className="h-8 w-20 bg-muted rounded" />
        <div className="h-6 w-48 bg-muted rounded" />
      </div>

      {/* Metadata panel skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-4 px-6 py-4 border-b animate-pulse">
        <div className="rounded-lg border bg-card p-3 space-y-2">
          <div className="h-4 w-3/4 bg-muted rounded" />
          <div className="flex gap-2">
            <div className="h-5 w-16 bg-muted rounded" />
            <div className="h-5 w-20 bg-muted rounded" />
          </div>
        </div>
        <div className="hidden sm:flex flex-col items-center justify-center px-4">
          <div className="h-8 w-8 bg-muted rounded" />
          <div className="h-3 w-24 bg-muted rounded mt-1" />
        </div>
        <div className="rounded-lg border bg-card p-3 space-y-2">
          <div className="h-4 w-3/4 bg-muted rounded" />
          <div className="flex gap-2">
            <div className="h-5 w-16 bg-muted rounded" />
            <div className="h-5 w-20 bg-muted rounded" />
          </div>
        </div>
      </div>

      {/* Toolbar skeleton */}
      <div className="flex items-center gap-2 px-6 py-2 border-b animate-pulse">
        <div className="h-8 w-36 bg-muted rounded" />
        <div className="h-8 w-28 bg-muted rounded" />
      </div>

      {/* Split view skeleton */}
      <div className="flex-1 overflow-hidden">
        <div className="hidden lg:grid grid-cols-2 h-full divide-x">
          {[0, 1].map((i) => (
            <div key={i} className="flex flex-col h-full animate-pulse">
              <div className="p-4 bg-muted/30 border-b">
                <div className="h-5 w-3/4 bg-muted rounded mb-2" />
                <div className="h-4 w-20 bg-muted rounded" />
              </div>
              <div className="flex-1 p-4 space-y-4">
                {Array.from({ length: 4 }).map((_, j) => (
                  <div key={j}>
                    <div className="h-4 w-16 bg-muted rounded mb-2" />
                    <div className="space-y-1.5">
                      <div className="h-3 w-full bg-muted rounded" />
                      <div className="h-3 w-5/6 bg-muted rounded" />
                      <div className="h-3 w-3/4 bg-muted rounded" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
