'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Menu, X } from 'lucide-react';
import { ModeToggle } from '@/components/mode-toggle';
import { LanguageToggle } from '@/components/LanguageToggle';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        home: 'Inicio',
        search: 'Buscar',
        explore: 'Explorar',
        categories: 'Categorías',
        states: 'Estados',
        compare: 'Comparar',
        favorites: 'Favoritos',
        openMenu: 'Abrir menú',
        closeMenu: 'Cerrar menú',
    },
    en: {
        home: 'Home',
        search: 'Search',
        explore: 'Explore',
        categories: 'Categories',
        states: 'States',
        compare: 'Compare',
        favorites: 'Favorites',
        openMenu: 'Open menu',
        closeMenu: 'Close menu',
    },
    nah: {
        home: 'Caltenco',
        search: 'Tlatemoliztli',
        explore: 'Tlaixmatiliztli',
        categories: 'Tlamantli',
        states: 'Altepetl',
        compare: 'Tlanānamiquiliztli',
        favorites: 'Tlapepenilistli',
        openMenu: 'Xictlapo tlahcuilōlli',
        closeMenu: 'Xictlatzacua tlahcuilōlli',
    },
};

const NAV_LINKS = [
    { href: '/', key: 'home' as const },
    { href: '/busqueda', key: 'search' as const },
    { href: '/leyes', key: 'explore' as const },
    { href: '/categorias', key: 'categories' as const },
    { href: '/estados', key: 'states' as const },
    { href: '/comparar', key: 'compare' as const },
    { href: '/favoritos', key: 'favorites' as const },
];

export function Navbar() {
    const { lang } = useLang();
    const t = content[lang];
    const pathname = usePathname();
    const isHome = pathname === '/';
    // Key mobile menu state to pathname — resets to false on navigation
    const [mobileState, setMobileState] = useState<{ path: string; open: boolean }>({ path: pathname, open: false });
    const mobileOpen = mobileState.path === pathname && mobileState.open;
    const setMobileOpen = (open: boolean) => setMobileState({ path: pathname, open });

    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 10);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const isTransparent = isHome && !scrolled && !mobileOpen;

    return (
        <nav
            className={`sticky top-0 z-40 transition-all duration-200 ${
                isTransparent
                    ? 'bg-transparent'
                    : 'bg-background/80 backdrop-blur-lg border-b border-border'
            }`}
        >
            <div className="mx-auto max-w-7xl px-4 sm:px-6">
                <div className="flex h-14 items-center justify-between">
                    {/* Brand */}
                    <Link href="/" className="flex items-center gap-2 font-bold text-lg">
                        <BookOpen className="h-5 w-5 text-primary" aria-hidden="true" />
                        <span>Tezca</span>
                    </Link>

                    {/* Desktop nav links */}
                    <div className="hidden md:flex items-center gap-1">
                        {NAV_LINKS.map((link) => {
                            const isActive = pathname === link.href;
                            return (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                                        isActive
                                            ? 'bg-primary/10 text-primary'
                                            : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                                    }`}
                                >
                                    {t[link.key]}
                                </Link>
                            );
                        })}
                    </div>

                    {/* Right side: toggles */}
                    <div className="flex items-center gap-2">
                        <div className="hidden sm:block">
                            <LanguageToggle />
                        </div>
                        <ModeToggle />
                        {/* Mobile hamburger */}
                        <button
                            className="md:hidden p-2 rounded-md hover:bg-muted/50 transition-colors"
                            onClick={() => setMobileOpen(!mobileOpen)}
                            aria-label={mobileOpen ? t.closeMenu : t.openMenu}
                            aria-expanded={mobileOpen}
                        >
                            {mobileOpen ? (
                                <X className="h-5 w-5" />
                            ) : (
                                <Menu className="h-5 w-5" />
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile slide panel */}
            {mobileOpen && (
                <div className="md:hidden border-t border-border bg-background/95 backdrop-blur-lg animate-slide-down">
                    <div className="px-4 py-4 space-y-1">
                        {NAV_LINKS.map((link) => {
                            const isActive = pathname === link.href;
                            return (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    className={`block px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                                        isActive
                                            ? 'bg-primary/10 text-primary'
                                            : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                                    }`}
                                >
                                    {t[link.key]}
                                </Link>
                            );
                        })}
                        <div className="pt-3 px-3 sm:hidden">
                            <LanguageToggle />
                        </div>
                    </div>
                </div>
            )}
        </nav>
    );
}
