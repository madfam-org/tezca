import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const viewport: Viewport = {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
};

export const metadata: Metadata = {
    title: {
        default: "Admin Console - Tezca",
        template: "%s — Tezca Admin",
    },
    description: "Consola administrativa para tezca.mx",
};

import { JanuaProvider, UserButton } from "@/lib/auth";
import { ThemeProvider } from "@/components/theme-provider";
import { ModeToggle } from "@/components/mode-toggle";

const januaConfig = {
    baseURL: process.env.NEXT_PUBLIC_JANUA_BASE_URL || "https://auth.madfam.io",
    apiKey: process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || "",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="es" suppressHydrationWarning>
            <body className={inter.className}>
                <JanuaProvider config={januaConfig}>
                    <ThemeProvider
                        attribute="class"
                        defaultTheme="system"
                        enableSystem
                        disableTransitionOnChange
                    >
                        <div className="min-h-screen bg-background text-foreground">
                            <header className="bg-card shadow-sm border-b">
                                <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
                                    <h1 className="text-2xl font-bold">
                                        Tezca Admin
                                    </h1>
                                    <div className="flex items-center gap-4">
                                        <ModeToggle />
                                        <UserButton
                                            showName={true}
                                            afterSignOutUrl="/sign-in"
                                        />
                                    </div>
                                </div>
                            </header>
                            <main>
                                <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                                    {children}
                                </div>
                            </main>
                        </div>
                    </ThemeProvider>
                </JanuaProvider>
            </body>
        </html>
    );
}
