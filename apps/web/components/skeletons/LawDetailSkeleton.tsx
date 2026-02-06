const TOC_WIDTHS = ['w-4/5', 'w-3/5', 'w-5/6', 'w-2/3', 'w-3/4', 'w-4/6', 'w-5/6', 'w-3/5'];

export function LawDetailSkeleton() {
    return (
        <div className="min-h-screen bg-background animate-pulse">
            {/* Header skeleton */}
            <div className="border-b bg-card">
                <div className="container mx-auto px-4 py-8">
                    <div className="flex gap-2 mb-4">
                        <div className="h-6 w-20 rounded bg-muted" />
                        <div className="h-6 w-16 rounded bg-muted" />
                    </div>
                    <div className="h-10 w-3/4 rounded bg-muted mb-4" />
                    <div className="h-4 w-48 rounded bg-muted" />
                </div>
            </div>
            {/* Content skeleton */}
            <div className="container mx-auto flex flex-col lg:flex-row gap-8 px-4 py-8">
                {/* TOC */}
                <aside className="lg:w-80 flex-shrink-0">
                    <div className="bg-card border rounded-lg p-4 space-y-3">
                        {TOC_WIDTHS.map((w, i) => (
                            <div key={i} className={`h-4 rounded bg-muted ${w}`} />
                        ))}
                    </div>
                </aside>
                {/* Articles */}
                <main className="flex-1 space-y-6">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="bg-card border rounded-lg p-6 space-y-3">
                            <div className="h-5 w-32 rounded bg-muted" />
                            <div className="h-4 w-full rounded bg-muted" />
                            <div className="h-4 w-5/6 rounded bg-muted" />
                            <div className="h-4 w-4/6 rounded bg-muted" />
                        </div>
                    ))}
                </main>
            </div>
        </div>
    );
}
