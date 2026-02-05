
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { LawArticleResponse } from "@leyesmx/lib";
import { Card, Badge, Button } from "@leyesmx/ui";
import Link from 'next/link';
import { ArrowLeft, Loader2, Map } from 'lucide-react';

interface ComparisonViewProps {
    lawIds: string[];
}

interface LawStructureNode {
    label: string;
    children: LawStructureNode[];
}

interface LawData {
    details: LawArticleResponse;
    structure: LawStructureNode[];
}

export default function ComparisonView({ lawIds }: ComparisonViewProps) {
    const [data, setData] = useState<LawData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Initial load
    useEffect(() => {
        async function fetchData() {
            if (lawIds.length < 2) {
                setLoading(false); 
                return;
            }

            try {
                setLoading(true);
                const promises = lawIds.map(async (id) => {
                    const [articles, structureData] = await Promise.all([
                        api.getLawArticles(id),
                        api.getLawStructure(id)
                    ]);
                    return {
                        details: articles,
                        structure: structureData.structure
                    };
                });

                const results = await Promise.all(promises);
                setData(results);
            } catch (err) {
                console.error("Comparison fetch error", err);
                setError("No se pudieron cargar las leyes.");
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, [lawIds]);

    if (loading) {
        return (
            <div className="flex h-[80vh] items-center justify-center flex-col px-4">
                <Loader2 className="h-8 w-8 sm:h-10 sm:w-10 animate-spin text-primary mb-4" />
                <h2 className="text-lg sm:text-xl font-medium text-center">Analizando estructura legal...</h2>
                <p className="text-muted-foreground text-xs sm:text-sm mt-2 text-center">Comparando {lawIds.length} documentos</p>
            </div>
        );
    }

    if (error) return <div className="text-destructive text-center p-6 sm:p-10 text-sm sm:text-base">{error}</div>;

    if (lawIds.length < 2) {
         return (
            <div className="flex flex-col items-center justify-center py-12 sm:py-20 px-4">
                <h2 className="text-xl sm:text-2xl font-bold mb-4 text-center">Selecciona leyes para comparar</h2>
                <p className="text-sm sm:text-base text-muted-foreground mb-6 max-w-md text-center">
                    Necesitas al menos dos leyes para usar la herramienta de comparación inteligente.
                </p>
                <Button asChild>
                    <Link href="/search">Ir al Buscador</Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-80px)]">
            {/* Header */}
            <div className="flex items-center gap-2 sm:gap-4 py-3 sm:py-4 px-4 sm:px-6 border-b">
                <Button asChild variant="ghost" size="sm">
                    <Link href="/search">
                        <ArrowLeft className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                        <span className="hidden sm:inline">Volver</span>
                        <span className="sm:hidden text-xs">Atrás</span>
                    </Link>
                </Button>
                <div>
                     <h1 className="text-base sm:text-xl font-bold flex items-center gap-2">
                        <Map className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                        <span className="hidden sm:inline">Comparación Estructural</span>
                        <span className="sm:hidden">Comparación</span>
                    </h1>
                </div>
            </div>

            {/* Split View */}
            <div className="flex-1 overflow-hidden">
                <div className="grid grid-cols-1 lg:grid-cols-2 h-full lg:divide-x">
                    {data.map((law, index) => (
                        <div key={law.details.law_id} className="flex flex-col h-full overflow-hidden border-b lg:border-b-0">
                            {/* Law Header */}
                            <div className="p-3 sm:p-4 bg-muted/30 border-b">
                                <h2 className="text-sm sm:text-base font-bold truncate" title={law.details.law_name}>
                                    {law.details.law_name}
                                </h2>
                                <div className="flex gap-2 mt-1">
                                    <Badge variant="outline" className="text-xs">{law.details.articles.length} artículos</Badge>
                                </div>
                            </div>
                            
                            {/* Content & Structure */}
                            <div className="flex-1 overflow-hidden flex">
                                {/* Structure Sidebar (Mini) */}
                                <div className="w-1/3 border-r overflow-y-auto bg-muted/10 p-2 hidden xl:block text-xs">
                                     <h3 className="font-semibold mb-2 text-muted-foreground uppercase tracking-wider text-[10px]">Estructura</h3>
                                     <StructureTree nodes={law.structure} />
                                </div>

                                {/* Main Text */}
                                <div className="flex-1 p-3 sm:p-4 overflow-y-auto">
                                    <div className="prose dark:prose-invert max-w-none text-xs sm:text-sm">
                                        {law.details.articles.map(article => (
                                            <div key={article.article_id} className="mb-4">
                                                <span className="font-bold text-primary block mb-1 sticky top-0 bg-background/90 backdrop-blur z-10 text-xs sm:text-sm">
                                                    {article.article_id}
                                                </span>
                                                <p className="whitespace-pre-wrap text-muted-foreground leading-relaxed text-xs sm:text-sm">
                                                    {article.text}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// Recursive Tree Component
function StructureTree({ nodes, level = 0 }: { nodes: LawStructureNode[], level?: number }) {
    if (!nodes || nodes.length === 0) return <div className="text-muted-foreground italic pl-2">Sin estructura</div>;

    return (
        <ul className={`space-y-1 ${level > 0 ? 'ml-2 border-l pl-2' : ''}`}>
             {nodes.map((node, i) => (
                 <li key={i}>
                     <div className="py-1 px-2 rounded hover:bg-muted cursor-pointer truncate" title={node.label}>
                         {node.label}
                     </div>
                     {node.children && node.children.length > 0 && (
                         <StructureTree nodes={node.children} level={level + 1} />
                     )}
                 </li>
             ))}
        </ul>
    );
}
