import Link from 'next/link';
import { Badge } from '@/components/ui/badge';

const popularLaws = [
    { id: 'constitucion', name: 'Constitución', href: '/laws/constitucion' },
    { id: 'codigo-civil', name: 'Código Civil', href: '/laws/codigo-civil' },
    { id: 'codigo-penal', name: 'Código Penal', href: '/laws/codigo-penal' },
    { id: 'isr', name: 'ISR', href: '/laws/isr' },
    { id: 'iva', name: 'IVA', href: '/laws/iva' },
    { id: 'trabajo', name: 'Ley Federal del Trabajo', href: '/laws/lft' },
    { id: 'imss', name: 'Seguro Social', href: '/laws/lss' },
    { id: 'amparo', name: 'Amparo', href: '/laws/amparo' },
];

export function PopularLaws() {
    return (
        <div className="mx-auto max-w-7xl px-6 py-16">
            <div className="mb-8 text-center">
                <h2 className="font-display text-2xl font-bold text-foreground sm:text-3xl">
                    📚 Leyes Populares
                </h2>
                <p className="mt-2 text-muted-foreground">
                    Acceso rápido a las leyes más consultadas
                </p>
            </div>

            <div className="flex flex-wrap justify-center gap-3">
                {popularLaws.map((law) => (
                    <Link key={law.id} href={law.href}>
                        <Badge
                            variant="secondary"
                            className="cursor-pointer px-6 py-3 text-base font-medium transition-all hover:scale-105 hover:bg-primary-100 hover:text-primary-700 dark:hover:bg-primary-900"
                        >
                            {law.name}
                        </Badge>
                    </Link>
                ))}
            </div>
        </div>
    );
}
