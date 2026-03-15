'use client';

import React, { createContext, useContext, useState, useCallback, useEffect, useSyncExternalStore } from 'react';
import { trackEvent } from '@/lib/analytics/posthog';

export type Lang = 'es' | 'en' | 'nah';

export const LOCALE_MAP: Record<Lang, string> = {
  es: 'es-MX',
  en: 'en-US',
  nah: 'es-MX', // Nahuatl uses MX locale for number/date formatting
};

interface LanguageContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const STORAGE_KEY = 'preferred-lang';

function getSnapshot(): Lang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'nah') return stored;
    return 'es';
  } catch {
    return 'es';
  }
}

function getServerSnapshot(): Lang {
  return 'es';
}

function subscribe(callback: () => void): () => void {
  window.addEventListener('storage', callback);
  return () => window.removeEventListener('storage', callback);
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const storedLang = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [override, setOverride] = useState<Lang | null>(null);
  const lang = override ?? storedLang;

  const setLang = useCallback((newLang: Lang) => {
    trackEvent('language.switched', { from: lang, to: newLang });
    setOverride(newLang);
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // localStorage unavailable
    }
  }, [lang]);

  useEffect(() => {
    document.documentElement.lang = lang === 'nah' ? 'nci' : lang;
  }, [lang]);

  return (
    <LanguageContext.Provider value={{ lang, setLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLang must be used within a LanguageProvider');
  }
  return context;
}
