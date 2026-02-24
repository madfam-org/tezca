"use client";

import { SignInForm } from "@/lib/auth";

export default function SignInPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="w-full max-w-md space-y-8 px-4">
                <div className="text-center">
                    <h2 className="text-3xl font-bold tracking-tight">
                        Tezca Admin
                    </h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Sign in to access the admin console
                    </p>
                </div>
                <SignInForm redirectTo="/" />
            </div>
        </div>
    );
}
