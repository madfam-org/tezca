'use client';

import { useComparison } from './providers/ComparisonContext';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { X } from 'lucide-react';

export default function ComparisonFloatingBar() {
    const { selectedLaws, clearSelection } = useComparison();

    if (selectedLaws.length === 0) return null;

    return (
        <div className="fixed bottom-0 left-0 right-0 p-4 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50 shadow-lg animate-in slide-in-from-bottom">
            <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center justify-between w-full sm:w-auto gap-4">
                    <span className="font-semibold text-sm sm:text-base">{selectedLaws.length} leyes seleccionadas</span>
                    <Button variant="ghost" size="sm" onClick={clearSelection} className="h-8 px-2">
                        <X className="w-4 h-4 mr-1" />
                        Limpiar
                    </Button>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                    {selectedLaws.length < 2 && (
                        <div className="text-sm text-muted-foreground self-center hidden sm:block mr-4">
                            Selecciona otra para comparar
                        </div>
                    )}
                    <Button
                        asChild
                        disabled={selectedLaws.length < 2}
                        variant={selectedLaws.length >= 2 ? "default" : "secondary"}
                        className="w-full sm:w-auto"
                    >
                        <Link href={`/compare?laws=${selectedLaws.join(',')}`}>
                            Comparar Leyes
                        </Link>
                    </Button>
                </div>
            </div>
        </div>
    );
}
