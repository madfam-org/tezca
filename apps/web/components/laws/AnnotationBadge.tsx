'use client';

import { MessageSquare } from 'lucide-react';
import { cn } from '@tezca/lib';

interface AnnotationBadgeProps {
    count: number;
    onClick: () => void;
    className?: string;
}

export function AnnotationBadge({ count, onClick, className }: AnnotationBadgeProps) {
    if (count === 0) return null;

    return (
        <button
            onClick={onClick}
            className={cn(
                'inline-flex items-center gap-1 px-1.5 py-0.5 text-xs rounded-full',
                'bg-primary/10 text-primary hover:bg-primary/20 transition-colors',
                className,
            )}
            aria-label={`${count} annotations`}
        >
            <MessageSquare className="h-3 w-3" />
            <span>{count}</span>
        </button>
    );
}
