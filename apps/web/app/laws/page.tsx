import { laws, getTotalArticles, getAverageQuality } from '@/lib/laws';
import LawCard from '@/components/LawCard';
import Link from 'next/link';

export default function LawsPage() {
    const totalArticles = getTotalArticles();
    const avgQuality = getAverageQuality();

    return (
        <div className="min-h-screen bg-gradient-to-br from-stone-50 to-stone-100 dark:from-gray-900 dark:to-stone-950">
            {/* Header */}
            <div className="bg-gradient-to-r from-crimson-600 to-crimson-800 dark:from-crimson-700 dark:to-crimson-950 text-white shadow-xl">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-4xl font-bold mb-2">
                                🇲🇽 Leyes Como Código
                            </h1>
                            <p className="text-xl text-crimson-100">
                                Legislación Federal en Formato Akoma Ntoso
                            </p>
                        </div>
                        <Link
                            href="/"
                            className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg transition-colors duration-200"
                        >
                            ← Inicio
                        </Link>
                    </div>
                </div>
            </div>

            {/* Stats */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border-l-4 border-crimson-600 hover:shadow-xl transition-shadow duration-200">
                        <div className="text-sm font-medium text-stone-600 dark:text-stone-400 uppercase tracking-wide">
                            Leyes Disponibles
                        </div>
                        <div className="text-3xl font-bold text-crimson-600 dark:text-crimson-400 mt-2">
                            {laws.length}
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border-l-4 border-forest-600 hover:shadow-xl transition-shadow duration-200">
                        <div className="text-sm font-medium text-stone-600 dark:text-stone-400 uppercase tracking-wide">
                            Artículos Totales
                        </div>
                        <div className="text-3xl font-bold text-forest-600 dark:text-forest-400 mt-2">
                            ~{(totalArticles / 1000).toFixed(1)}k
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border-l-4 border-gold-500 hover:shadow-xl transition-shadow duration-200">
                        <div className="text-sm font-medium text-stone-600 dark:text-stone-400 uppercase tracking-wide">
                            Calificación Promedio
                        </div>
                        <div className="text-3xl font-bold text-gold-600 dark:text-gold-400 mt-2">
                            {avgQuality.toFixed(1)}%
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border-l-4 border-stone-700 hover:shadow-xl transition-shadow duration-200">
                        <div className="text-sm font-medium text-stone-600 dark:text-stone-400 uppercase tracking-wide">
                            Validación Schema
                        </div>
                        <div className="text-3xl font-bold text-stone-700 dark:text-stone-300 mt-2">
                            100%
                        </div>
                    </div>
                </div>

                {/* Laws Grid */}
                <div className="mb-8">
                    <h2 className="text-2xl font-bold text-stone-900 dark:text-white mb-6">
                        Leyes Federales
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {laws.map((law) => (
                            <LawCard key={law.id} law={law} />
                        ))}
                    </div>
                </div>

                {/* Info Footer */}
                <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border-l-4 border-crimson-600">
                    <h3 className="text-lg font-semibold text-stone-900 dark:text-white mb-3">
                        Sobre este visor
                    </h3>
                    <p className="text-stone-600 dark:text-stone-400 mb-3">
                        Este visor presenta 10 leyes federales mexicanas convertidas al estándar internacional
                        <strong className="text-stone-900 dark:text-white"> Akoma Ntoso 3.0</strong>,
                        un formato estructurado XML para documentos legales.
                    </p>
                    <div className="flex gap-4 text-sm text-stone-500 dark:text-stone-500">
                        <span>✅ 100% validación de schema</span>
                        <span>✅ ~8,000 artículos procesados</span>
                        <span className="text-forest-600 font-medium">✅ Formato machine-readable</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

