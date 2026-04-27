'use client';

import { Button } from "@tezca/ui";
import { Link2, Unlink2, Copy, Check } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';

const content = {
    es: {
        syncOn: 'Scroll sincronizado',
        syncOff: 'Sincronizar scroll',
        copied: 'Copiado!',
        copyLink: 'Copiar enlace',
    },
    en: {
        syncOn: 'Scroll synced',
        syncOff: 'Sync scroll',
        copied: 'Copied!',
        copyLink: 'Copy link',
    },
    nah: {
        syncOn: 'Tlanānamiquiliztli tlaōlinaliztli',
        syncOff: 'Xictlanānamiqui tlaōlinaliztli',
        copied: 'Ōmocopi!',
        copyLink: 'Xiccopīna tlahcuilōltzintli',
    },
};

interface ComparisonToolbarProps {
    syncScroll: boolean;
    onToggleSync: () => void;
}

export function ComparisonToolbar({ syncScroll, onToggleSync }: ComparisonToolbarProps) {
    const { lang } = useLang();
    const t = content[lang];
    const { copied, copy } = useCopyToClipboard();

    const handleCopyUrl = () => {
        void copy(window.location.href);
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
                    {syncScroll ? t.syncOn : t.syncOff}
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
                    {copied ? t.copied : t.copyLink}
                </span>
                <span className="sm:hidden">
                    {copied ? 'OK' : 'URL'}
                </span>
            </Button>
        </div>
    );
}
