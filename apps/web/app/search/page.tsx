import SearchExperience from '@/components/SearchExperience';

export default function SearchPage() {
    return (
        <main className="min-h-screen bg-gray-50 py-12">
            <div className="container mx-auto">
                <h1 className="text-4xl font-black text-center mb-8 text-gray-900 tracking-tight">
                    Leyes Como Código <span className="text-blue-600">Buscador</span>
                </h1>
                <SearchExperience />
            </div>
        </main>
    );
}
