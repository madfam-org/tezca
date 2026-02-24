"use client";

import Link from "next/link";
import { SignInForm } from "@/lib/auth";

const januaConfigured = !!process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY;

export default function SignInPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="w-full max-w-md space-y-8 px-4">
                <div className="text-center">
                    <h2 className="text-3xl font-bold tracking-tight">
                        Tezca Admin
                    </h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                        {januaConfigured
                            ? "Inicia sesión para acceder a la consola"
                            : "Autenticación no configurada"}
                    </p>
                </div>

                {januaConfigured ? (
                    <SignInForm redirectTo="/" />
                ) : (
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
                )}
            </div>
        </div>
    );
}
