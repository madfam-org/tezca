import { Hero } from '@/components/Hero';
import { JurisdictionCards } from '@/components/JurisdictionCards';
import { DashboardStatsGrid, RecentLawsList } from '@/components/DashboardStats';
import { PopularLaws } from '@/components/PopularLaws';
import { DynamicFeatures } from '@/components/DynamicFeatures';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Hero />

      <div className="container mx-auto px-4 sm:px-6 -mt-10 relative z-10">
        <DashboardStatsGrid />
      </div>

      <div className="container mx-auto px-4 sm:px-6 py-12 sm:py-16 space-y-12 sm:space-y-16">

        <div className="grid gap-6 sm:gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6 sm:space-y-8">
            <section>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight mb-4 sm:mb-6">Explorar por Jurisdicción</h2>
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

        {/* Features section - dynamically populated from API */}
        <DynamicFeatures />
      </div>
    </div>
  );
}
