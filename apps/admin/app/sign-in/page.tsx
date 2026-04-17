"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { SignIn } from "@janua/ui/components/auth";
import { Shield } from "lucide-react";

const januaConfigured = !!process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

export default function SignInPage() {
    const router = useRouter();

    if (!januaConfigured) {
        return <UnconfiguredFallback />;
    }

    return (
        <Suspense
            fallback={
                <PageShell subtitle="Cargando...">
                    <div className="flex justify-center py-8">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    </div>
                </PageShell>
            }
        >
            <SignInFormContent router={router} />
        </Suspense>
    );
}

function SignInFormContent({
    router,
}: {
    router: ReturnType<typeof useRouter>;
}) {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const searchParams = useSearchParams();
    const ssoError = searchParams.get("sso_error");

    useEffect(() => {
        if (isAuthenticated && !authLoading) {
            router.replace("/");
        }
    }, [isAuthenticated, authLoading, router]);

    function handleSsoLogin() {
        // Navigate to the server-side OIDC initiation route
        window.location.href = "/api/auth/sso";
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
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
            <div className="w-full max-w-md space-y-6">
                {/* Header */}
                <div className="text-center">
                    <h2 className="text-3xl font-bold tracking-tight">
                        Iniciar sesión
                    </h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Bienvenido de nuevo
                    </p>
                </div>

                {/* SSO Error */}
                {ssoError && (
                    <div
                        role="alert"
                        className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
                    >
                        {ssoError}
                    </div>
                )}

                {/* Enterprise SSO Button */}
                <div className="space-y-3">
                    <button
                        onClick={handleSsoLogin}
                        className="w-full flex justify-center items-center gap-2 rounded-md bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
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
                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-border" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground">
                            o usa correo y contraseña
                        </span>
                    </div>
                </div>

                {/* @janua/ui SignIn component for email/password + social providers */}
                <SignIn
                    apiUrl=""
                    socialProviders={{ google: true, github: true }}
                    showRememberMe={true}
                    afterSignIn={() => {
                        // Full reload so AdminAuthBridge hydrates SDK
                        // state from the janua-session cookie via /api/auth/me
                        window.location.href = "/";
                    }}
                    onError={(error) => {
                        console.error("Sign-in error:", error.message);
                    }}
                />

                {/* Legal links */}
                <p className="text-center text-xs text-muted-foreground">
                    Al continuar, aceptas los{" "}
                    <a
                        href="https://tezca.mx/terms"
                        className="underline hover:text-foreground"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Términos de Servicio
                    </a>{" "}
                    y la{" "}
                    <a
                        href="https://tezca.mx/privacy"
                        className="underline hover:text-foreground"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Política de Privacidad
                    </a>
                    .
                </p>
            </div>
        </div>
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
                    Para habilitar autenticación, agrega las siguientes
                    variables:
                </p>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {`NEXT_PUBLIC_JANUA_ISSUER_URL=https://auth.madfam.io
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
