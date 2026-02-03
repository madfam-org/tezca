import { Hero } from '@/components/Hero';
import { JurisdictionCards } from '@/components/JurisdictionCards';
import { DashboardStatsGrid, RecentLawsList } from '@/components/DashboardStats';
import { PopularLaws } from '@/components/PopularLaws';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Hero />

      <div className="container mx-auto px-4 -mt-10 relative z-10">
        <DashboardStatsGrid />
      </div>

      <div className="container mx-auto px-4 py-16 space-y-16">

        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            <section>
              <h2 className="text-2xl font-bold tracking-tight mb-6">Explorar por Jurisdicción</h2>
              <JurisdictionCards />
            </section>

            <section>
              <PopularLaws />
            </section>
          </div>

          <aside>
            <RecentLawsList />
          </aside>
        </div>

        {/* Features section */}
        <div className="rounded-2xl border border-border bg-muted/30 p-8 md:p-12">
          <div className="grid gap-8 md:grid-cols-3">
            <Feature
              icon="✨"
              title="87% Cobertura Legal"
              description="Mas de 10,000 leyes federales y estatales completamente digitalizadas" />
            <Feature
              icon="🔍"
              title="Búsqueda Completa"
              description="550,000+ artículos indexados con búsqueda de texto completo"
            />
            <Feature
              icon="📊"
              title="98.9% Precisión"
              description="Calidad garantizada con validación automática y sistema de calificación"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Feature({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="mb-4 text-4xl">{icon}</div>
      <h3 className="font-display text-lg font-bold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
