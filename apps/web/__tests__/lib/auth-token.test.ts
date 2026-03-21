import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getAuthToken } from '@/lib/auth-token';

describe('getAuthToken', () => {
    beforeEach(() => {
        // Clear cookies and localStorage between tests
        Object.defineProperty(document, 'cookie', {
            writable: true,
            value: '',
        });
        localStorage.clear();
    });

    it('returns token from cookie when present', () => {
        Object.defineProperty(document, 'cookie', {
            writable: true,
            value: 'janua_token=my-cookie-token',
        });

        expect(getAuthToken()).toBe('my-cookie-token');
    });

    it('returns token from localStorage when cookie is absent', () => {
        localStorage.setItem('janua_token', 'my-local-token');

        expect(getAuthToken()).toBe('my-local-token');
    });

    it('prefers cookie over localStorage', () => {
        Object.defineProperty(document, 'cookie', {
            writable: true,
            value: 'janua_token=cookie-val',
        });
        localStorage.setItem('janua_token', 'local-val');

        expect(getAuthToken()).toBe('cookie-val');
    });

    it('returns null when neither cookie nor localStorage has a token', () => {
        expect(getAuthToken()).toBeNull();
    });
});
