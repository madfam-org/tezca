import type { Metadata, Viewport } from "next";
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600", "700"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Tezca — El Espejo de la Ley",
  description: "Plataforma de legislación mexicana abierta. 30,000+ leyes federales, estatales y municipales en formato digital con búsqueda avanzada y referencias cruzadas. Open Mexican law platform.",
  keywords: ["leyes mexicanas", "legislación mexicana", "leyes federales", "leyes estatales", "código civil", "Akoma Ntoso", "México", "Mexican law", "Tezca"],
  alternates: {
    canonical: SITE_URL,
    languages: {
      'es': SITE_URL,
      'en': `${SITE_URL}?lang=en`,
      'x-default': SITE_URL,
    },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "hsl(var(--primary))" },
    { media: "(prefers-color-scheme: dark)", color: "hsl(var(--primary))" },
  ],
};

import { JanuaProvider } from "@janua/nextjs";
import { ThemeProvider } from "@/components/theme-provider";
import { ComparisonProvider } from "@/components/providers/ComparisonContext";
import { LanguageProvider } from "@/components/providers/LanguageContext";
import { BookmarksProvider } from "@/components/providers/BookmarksContext";
import { AuthProvider } from "@/components/providers/AuthContext";
import ComparisonFloatingBar from "@/components/ComparisonFloatingBar";
import { Footer } from "@/components/Footer";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Navbar } from "@/components/Navbar";
import { ReadingProgressBar } from "@/components/ReadingProgressBar";
import { BackToTop } from "@/components/BackToTop";

const januaConfig = {
  baseURL: process.env.NEXT_PUBLIC_JANUA_BASE_URL || 'https://auth.madfam.io',
  apiKey: process.env.NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY || '',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${sourceSerif.variable} ${jetbrainsMono.variable} font-sans antialiased min-h-screen flex flex-col bg-background text-foreground`}
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-background focus:text-foreground focus:px-4 focus:py-2 focus:rounded-md focus:ring-2 focus:ring-ring"
        >
          Ir al contenido
        </a>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <ErrorBoundary>
            <JanuaProvider config={januaConfig}>
              <LanguageProvider>
                <AuthProvider>
                  <BookmarksProvider>
                    <ComparisonProvider>
                      <ReadingProgressBar />
                      <Navbar />
                      <main id="main-content" className="flex-1">{children}</main>
                      <Footer />
                      <ComparisonFloatingBar />
                      <BackToTop />
                    </ComparisonProvider>
                  </BookmarksProvider>
                </AuthProvider>
              </LanguageProvider>
            </JanuaProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
