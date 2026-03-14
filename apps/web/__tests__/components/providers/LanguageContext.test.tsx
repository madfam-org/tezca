import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { LanguageProvider, useLang, LOCALE_MAP } from '@/components/providers/LanguageContext';

/** Helper component that exposes LanguageContext values for testing. */
function LangDisplay() {
    const { lang, setLang } = useLang();
    return (
        <div>
            <span data-testid="lang">{lang}</span>
            <button data-testid="set-es" onClick={() => setLang('es')}>ES</button>
            <button data-testid="set-en" onClick={() => setLang('en')}>EN</button>
            <button data-testid="set-nah" onClick={() => setLang('nah')}>NAH</button>
        </div>
    );
}

describe('LanguageContext', () => {
    beforeEach(() => {
        localStorage.removeItem('preferred-lang');
        document.documentElement.lang = '';
    });

    // ---------------------------------------------------------------
    // 1. Default language is Spanish
    // ---------------------------------------------------------------
    it('defaults to Spanish (es) when localStorage is empty', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        expect(screen.getByTestId('lang').textContent).toBe('es');
    });

    // ---------------------------------------------------------------
    // 2. Provider renders children
    // ---------------------------------------------------------------
    it('renders children correctly', () => {
        render(
            <LanguageProvider>
                <span data-testid="child">Content</span>
            </LanguageProvider>,
        );

        expect(screen.getByTestId('child').textContent).toBe('Content');
    });

    // ---------------------------------------------------------------
    // 3. Switching to English
    // ---------------------------------------------------------------
    it('switches language to English', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        fireEvent.click(screen.getByTestId('set-en'));
        expect(screen.getByTestId('lang').textContent).toBe('en');
    });

    // ---------------------------------------------------------------
    // 4. Switching to Nahuatl
    // ---------------------------------------------------------------
    it('switches language to Nahuatl', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        fireEvent.click(screen.getByTestId('set-nah'));
        expect(screen.getByTestId('lang').textContent).toBe('nah');
    });

    // ---------------------------------------------------------------
    // 5. Persists language choice to localStorage
    // ---------------------------------------------------------------
    it('persists language choice to localStorage', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        fireEvent.click(screen.getByTestId('set-en'));
        expect(localStorage.getItem('preferred-lang')).toBe('en');
    });

    // ---------------------------------------------------------------
    // 6. Reads persisted language from localStorage
    // ---------------------------------------------------------------
    it('reads persisted language from localStorage on mount', () => {
        localStorage.setItem('preferred-lang', 'nah');

        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        expect(screen.getByTestId('lang').textContent).toBe('nah');
    });

    // ---------------------------------------------------------------
    // 7. Falls back to 'es' for invalid localStorage value
    // ---------------------------------------------------------------
    it('falls back to "es" for invalid localStorage value', () => {
        localStorage.setItem('preferred-lang', 'invalid');

        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        expect(screen.getByTestId('lang').textContent).toBe('es');
    });

    // ---------------------------------------------------------------
    // 8. LOCALE_MAP has correct entries
    // ---------------------------------------------------------------
    it('LOCALE_MAP contains correct locale strings', () => {
        expect(LOCALE_MAP.es).toBe('es-MX');
        expect(LOCALE_MAP.en).toBe('en-US');
        expect(LOCALE_MAP.nah).toBe('es-MX');
    });

    // ---------------------------------------------------------------
    // 9. Sets document.documentElement.lang on change
    // ---------------------------------------------------------------
    it('sets document.documentElement.lang to "es" for Spanish', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        expect(document.documentElement.lang).toBe('es');
    });

    // ---------------------------------------------------------------
    // 10. Sets document.documentElement.lang to "nci" for Nahuatl
    // ---------------------------------------------------------------
    it('sets document.documentElement.lang to "nci" for Nahuatl', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        fireEvent.click(screen.getByTestId('set-nah'));
        expect(document.documentElement.lang).toBe('nci');
    });

    // ---------------------------------------------------------------
    // 11. useLang throws outside provider
    // ---------------------------------------------------------------
    it('useLang throws when used outside LanguageProvider', () => {
        const consoleError = console.error;
        console.error = vi.fn();

        expect(() => render(<LangDisplay />)).toThrow(
            'useLang must be used within a LanguageProvider',
        );

        console.error = consoleError;
    });

    // ---------------------------------------------------------------
    // 12. Switching back to Spanish
    // ---------------------------------------------------------------
    it('switches back to Spanish after changing to English', () => {
        render(
            <LanguageProvider>
                <LangDisplay />
            </LanguageProvider>,
        );

        fireEvent.click(screen.getByTestId('set-en'));
        expect(screen.getByTestId('lang').textContent).toBe('en');

        fireEvent.click(screen.getByTestId('set-es'));
        expect(screen.getByTestId('lang').textContent).toBe('es');
    });
});
