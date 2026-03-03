export default function CuentaLoading() {
    return (
        <div className="min-h-screen bg-background">
            <div className="max-w-4xl mx-auto px-4 py-12">
                <div className="animate-pulse space-y-6">
                    <div className="h-8 bg-muted rounded w-36" />
                    <div className="h-24 rounded-xl bg-muted" />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="h-16 rounded-lg bg-muted" />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
