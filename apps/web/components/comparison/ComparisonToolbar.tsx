'use client';

import { useState } from 'react';
import { Button } from "@leyesmx/ui";
import { Link2, Unlink2, Copy, Check } from 'lucide-react';

interface ComparisonToolbarProps {
    syncScroll: boolean;
    onToggleSync: () => void;
}

export function ComparisonToolbar({ syncScroll, onToggleSync }: ComparisonToolbarProps) {
    const [copied, setCopied] = useState(false);

    const handleCopyUrl = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback: ignore if clipboard API unavailable
        }
    };

    return (
        <div className="flex items-center gap-2 px-4 sm:px-6 py-2 border-b bg-muted/10">
            <Button
                variant={syncScroll ? 'default' : 'outline'}
                size="sm"
                onClick={onToggleSync}
                className="gap-1.5 text-xs"
            >
                {syncScroll ? (
                    <Link2 className="h-3.5 w-3.5" />
                ) : (
                    <Unlink2 className="h-3.5 w-3.5" />
                )}
                <span className="hidden sm:inline">
                    {syncScroll ? 'Scroll sincronizado' : 'Sincronizar scroll'}
                </span>
                <span className="sm:hidden">
                    {syncScroll ? 'Sync ON' : 'Sync'}
                </span>
            </Button>

            <Button
                variant="outline"
                size="sm"
                onClick={handleCopyUrl}
                className="gap-1.5 text-xs"
            >
                {copied ? (
                    <Check className="h-3.5 w-3.5" />
                ) : (
                    <Copy className="h-3.5 w-3.5" />
                )}
                <span className="hidden sm:inline">
                    {copied ? 'Copiado!' : 'Copiar enlace'}
                </span>
                <span className="sm:hidden">
                    {copied ? 'OK' : 'URL'}
                </span>
            </Button>
        </div>
    );
}
