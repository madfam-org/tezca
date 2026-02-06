import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Building2, Scale, Home } from 'lucide-react';

const jurisdictions = [
    {
        id: 'federal',
        name: 'Federal',
        Icon: Scale,
        count: 333,
        coverage: 99.1,
        colorClass: 'primary',
        gradient: 'from-primary-500 to-primary-600',
        href: '/laws/federal',
        comingSoon: false,
    },
    {
        id: 'state',
        name: 'Estatal',
        Icon: Building2,
        count: 11363,
        coverage: 94,
        colorClass: 'secondary',
        gradient: 'from-secondary-500 to-secondary-600',
        href: '/laws/state',
        comingSoon: false,
    },
    {
        id: 'municipal',
        name: 'Municipal',
        Icon: Home,
        count: 217,
        coverage: 12,
        colorClass: 'accent',
        gradient: 'from-accent-500 to-accent-600',
        href: '/laws/municipal',
        comingSoon: false,
    },
] as const;

export function JurisdictionCards() {
    return (
        <div className="mx-auto max-w-7xl px-6 py-16">
            <div className="mb-12 text-center">
                <h2 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
                    Cobertura por Jurisdicción
                </h2>
                <p className="mt-3 text-lg text-muted-foreground">
                    Explora leyes federales, estatales y municipales
                </p>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {jurisdictions.map((jurisdiction) => (
                    <Link
                        key={jurisdiction.id}
                        href={jurisdiction.comingSoon ? '#' : jurisdiction.href}
                        className={`group block transition-transform ${jurisdiction.comingSoon ? 'cursor-not-allowed' : 'hover:-translate-y-1'
                            }`}
                    >
                        <Card className={`relative h-full overflow-hidden border-2 transition-all ${jurisdiction.comingSoon
                                ? 'opacity-75'
                                : 'hover:border-primary-300 hover:shadow-lg'
                            }`}>
                            {/* Background gradient */}
                            <div className={`absolute inset-0 bg-gradient-to-br ${jurisdiction.gradient} opacity-5`} />

                            <CardContent className="relative p-8">
                                {/* Icon */}
                                <div className={`mb-6 inline-flex rounded-xl bg-gradient-to-br ${jurisdiction.gradient} p-4 shadow-lg`}>
                                    <jurisdiction.Icon className="h-10 w-10 text-white" />
                                </div>

                                {/* Name */}
                                <h3 className="font-display text-2xl font-bold text-foreground mb-4">
                                    {jurisdiction.name}
                                </h3>

                                {/* Stats */}
                                <div className="space-y-4">
                                    <div className="flex items-baseline gap-3">
                                        <span className="font-display text-4xl font-bold text-foreground">
                                            {jurisdiction.count.toLocaleString('es-MX')}
                                        </span>
                                        <span className="text-base text-muted-foreground">leyes</span>
                                    </div>

                                    {/* Progress bar */}
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-sm font-medium">
                                            <span className="text-muted-foreground">Cobertura</span>
                                            <span className="text-foreground">{jurisdiction.coverage}%</span>
                                        </div>
                                        <div className="h-3 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
                                            <div
                                                className={`h-full rounded-full bg-gradient-to-r ${jurisdiction.gradient} transition-all duration-500`}
                                                style={{ width: `${jurisdiction.coverage}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Coming soon badge */}
                                {jurisdiction.comingSoon && (
                                    <Badge variant="outline" className="mt-6 border-accent-500 text-accent-600">
                                        Próximamente
                                    </Badge>
                                )}
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>
        </div>
    );
}
