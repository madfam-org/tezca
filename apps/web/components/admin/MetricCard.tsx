'use client';

import { Card, CardContent } from "@leyesmx/ui";
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
    title: string;
    value: string | number;
    trend?: string;
    status?: 'success' | 'warning' | 'error' | 'info';
    icon?: LucideIcon;
    description?: string;
}

export function MetricCard({ 
    title, 
    value, 
    trend, 
    status, 
    icon: Icon,
    description 
}: MetricCardProps) {
    const statusColors = {
        success: 'text-green-600 dark:text-green-400',
        warning: 'text-yellow-600 dark:text-yellow-400',
        error: 'text-red-600 dark:text-red-400',
        info: 'text-blue-600 dark:text-blue-400',
    };

    const trendColor = trend?.startsWith('+') 
        ? 'text-green-600 dark:text-green-400' 
        : trend?.startsWith('-') 
        ? 'text-red-600 dark:text-red-400' 
        : 'text-muted-foreground';

    return (
        <Card className="hover:shadow-md transition-shadow">
            <CardContent className="p-4 sm:p-6">
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <p className="text-xs sm:text-sm font-medium text-muted-foreground uppercase tracking-wider">
                            {title}
                        </p>
                        <div className="mt-2 flex items-baseline gap-2">
                            <h3 className={cn(
                                "text-2xl sm:text-3xl font-bold",
                                status ? statusColors[status] : 'text-foreground'
                            )}>
                                {value}
                            </h3>
                            {trend && (
                                <span className={cn("text-xs sm:text-sm font-medium", trendColor)}>
                                    {trend}
                                </span>
                            )}
                        </div>
                        {description && (
                            <p className="mt-1 text-xs text-muted-foreground">
                                {description}
                            </p>
                        )}
                    </div>
                    {Icon && (
                        <div className={cn(
                            "p-2 sm:p-3 rounded-lg",
                            status ? `bg-${status === 'success' ? 'green' : status === 'warning' ? 'yellow' : status === 'error' ? 'red' : 'blue'}-100 dark:bg-${status === 'success' ? 'green' : status === 'warning' ? 'yellow' : status === 'error' ? 'red' : 'blue'}-900/20` : 'bg-muted'
                        )}>
                            <Icon className={cn(
                                "h-4 w-4 sm:h-5 sm:w-5",
                                status ? statusColors[status] : 'text-muted-foreground'
                            )} />
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
