import { Hero } from '@/components/Hero';
import { JurisdictionCards } from '@/components/JurisdictionCards';
import { PopularLaws } from '@/components/PopularLaws';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Hero />
      <JurisdictionCards />
      <PopularLaws />

      {/* Features section */}
      <div className="border-t border-border bg-muted/30 py-16">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid gap-12 md:grid-cols-3">
            <Feature
              icon="✨"
              title="87% Cobertura Legal"
              description="11,667 leyes federales y estatales completamente digitalizadas" />
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
      <div className="mb-4 text-5xl">{icon}</div>
      <h3 className="font-display text-xl font-bold text-foreground mb-3">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}
