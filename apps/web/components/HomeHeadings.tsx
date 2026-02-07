'use client';

import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: 'Explorar por Jurisdicción',
    en: 'Explore by Jurisdiction',
    nah: 'Xictlachiya ic Tēyācanaliztli',
};

export function HomeHeadings() {
    const { lang } = useLang();
    return (
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight mb-4 sm:mb-6">
            {content[lang]}
        </h2>
    );
}
