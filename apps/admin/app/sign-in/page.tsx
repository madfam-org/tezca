"use client";

import { useState, useEffect, FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Shield } from "lucide-react";

const januaConfigured = !!process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

export default function SignInPage() {
    const router = useRouter();

    if (!januaConfigured) {
        return <UnconfiguredFallback />;
    }

    return <SignInFormContent router={router} />;
}

function SignInFormContent({ router }: { router: ReturnType<typeof useRouter> }) {
    const { auth, isAuthenticated, isLoading: authLoading } = useAuth();
    const searchParams = useSearchParams();
    const [ssoError, setSsoError] = useState<string | null>(null);

    // Email/password fallback state
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [formError, setFormError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (isAuthenticated && !authLoading) {
            router.replace("/");
        }
    }, [isAuthenticated, authLoading, router]);

    // Pick up SSO errors from callback redirect
    useEffect(() => {
        const error = searchParams.get("sso_error");
        if (error) {
            setSsoError(error);
        }
    }, [searchParams]);

    function handleSsoLogin() {
        // Navigate to the server-side OIDC initiation route
        window.location.href = "/api/auth/sso";
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setFormError(null);
        setSubmitting(true);
        try {
            await auth.signIn({ email, password });
            router.replace("/");
        } catch (err) {
            setFormError(
                err instanceof Error
                    ? err.message
                    : "Error al iniciar sesión. Verifica tus credenciales."
            );
        } finally {
            setSubmitting(false);
        }
    }

    if (authLoading) {
        return (
            <PageShell subtitle="Cargando...">
                <div className="flex justify-center py-8">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
            </PageShell>
        );
    }

    return (
        <PageShell subtitle="Inicia sesión para acceder a la consola">
            {/* SSO Button */}
            <div className="space-y-3">
                {ssoError && (
                    <div
                        role="alert"
                        className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
                    >
                        {ssoError}
                    </div>
                )}

                <button
                    onClick={handleSsoLogin}
                    className="w-full flex justify-center items-center gap-2 rounded-md bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                    <Shield className="h-4 w-4" />
                    Iniciar sesión con Janua SSO
                </button>

                <p className="text-center text-xs text-muted-foreground">
                    Serás redirigido al proveedor de identidad de tu
                    organización.
                </p>
            </div>

            {/* Divider */}
            <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">
                        o usa correo y contraseña
                    </span>
                </div>
            </div>

            {/* Email/password fallback form */}
            <form onSubmit={handleSubmit} className="space-y-4">
                {formError && (
                    <div
                        role="alert"
                        className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
                    >
                        {formError}
                    </div>
                )}

                <div className="space-y-2">
                    <label
                        htmlFor="email"
                        className="block text-sm font-medium text-foreground"
                    >
                        Correo electrónico
                    </label>
                    <input
                        id="email"
                        name="email"
                        type="email"
                        autoComplete="email"
                        required
                        value={email}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                        disabled={submitting}
                        placeholder="admin@madfam.io"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                    />
                </div>

                <div className="space-y-2">
                    <label
                        htmlFor="password"
                        className="block text-sm font-medium text-foreground"
                    >
                        Contraseña
                    </label>
                    <input
                        id="password"
                        name="password"
                        type="password"
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                        disabled={submitting}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                    />
                </div>

                <button
                    type="submit"
                    disabled={submitting}
                    className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                    {submitting ? "Iniciando sesión..." : "Iniciar sesión"}
                </button>
            </form>
        </PageShell>
    );
}

function PageShell({
    subtitle,
    children,
}: {
    subtitle: string;
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="w-full max-w-md space-y-8 px-4">
                <div className="text-center">
                    <h2 className="text-3xl font-bold tracking-tight">
                        Tezca Admin
                    </h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                        {subtitle}
                    </p>
                </div>
                {children}
            </div>
        </div>
    );
}

function UnconfiguredFallback() {
    return (
        <PageShell subtitle="Autenticación no configurada">
            <div className="rounded-lg border bg-muted/50 p-6 space-y-4">
                <p className="text-sm text-muted-foreground">
                    Las variables de entorno de Janua no están configuradas.
                    Para habilitar autenticación, agrega las siguientes variables:
                </p>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
{`NEXT_PUBLIC_JANUA_BASE_URL=https://auth.madfam.io
NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY=jnc_...
JANUA_SECRET_KEY=jns_...`}
                </pre>
                <Link
                    href="/"
                    className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    Continuar sin autenticación
                </Link>
            </div>
        </PageShell>
    );
}
