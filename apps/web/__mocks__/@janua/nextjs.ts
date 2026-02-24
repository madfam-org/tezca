/**
 * Test stub for @janua/nextjs — used by vitest when the real package
 * isn't installed (local dev without npm.madfam.io registry access).
 */
import React from 'react';

export function JanuaProvider({ children }: { children: React.ReactNode; config?: unknown }) {
    return children as React.ReactElement;
}

export function UserButton() {
    return null;
}

export function SignInForm() {
    return null;
}

export function useAuth() {
    return { auth: null, user: null, session: null, isAuthenticated: false, isLoading: false, signOut: async () => {} };
}

export function useJanua() {
    return { client: null, user: null, session: null, isLoading: false, isAuthenticated: false, signOut: async () => {}, updateUser: async () => {} };
}

export function useUser() {
    return { user: null, isLoading: false, updateUser: async () => {} };
}

export class JanuaServerClient {
    constructor(_config: unknown) {}
    async getSession() { return null; }
    async requireAuth() { throw new Error('Not authenticated'); }
    async signIn() { return { user: null, session: null }; }
    async signOut() {}
}

export function SignedIn({ children }: { children: React.ReactNode }) { return null; }
export function SignedOut({ children }: { children: React.ReactNode }) { return children as React.ReactElement; }
