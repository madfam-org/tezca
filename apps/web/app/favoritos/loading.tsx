export default function FavoritosLoading() {
    return (
        <div className="min-h-screen bg-background">
            <div className="max-w-4xl mx-auto px-4 py-12">
                <div className="animate-pulse space-y-6">
                    <div className="h-8 bg-muted rounded w-48" />
                    <div className="space-y-4">
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="h-20 rounded-xl bg-muted" />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
