# Public Portal (Web)

The citizen-facing web application for searching and reading Mexican laws.

## Features
- **Law Search**: Full-text search with faceted filters (tier, category, status, law_type, state) and autocomplete typeahead.
- **Faceted Aggregations**: Live result counts from Elasticsearch (by_tier, by_category, by_status, by_law_type, by_state).
- **Law Visualization**: Clean, readable presentation with hierarchical TOC (tree/flat toggle), version timeline, cross-reference panel.
- **Comparison**: Side-by-side law comparison with word-level diff highlighting, sync scroll, metadata panel, and mobile tabs.
- **6-Format Export**: TXT/PDF/LaTeX/DOCX/EPUB/JSON with tier-based rate limits (anon/free/premium).
- **Related Laws**: Elasticsearch more_like_this recommendations on law detail pages.
- **Cmd+K Search**: Global search overlay with debounced suggestions and keyboard navigation.
- **Citation Export**: Legal citation + BibTeX copy from article viewer.
- **Browse Pages**: Browse by Category (/categorias/) and by State (/estados/) with API-backed counts.
- **Dashboard**: Real-time statistics with 6-card grid (federal, state, municipal, legislative, non-legislative, articles).
- **Legal Pages**: Terms & Conditions, Legal Disclaimer, Privacy Policy — trilingual ES/EN/NAH.
- **Site Footer**: Navigation links, official sources, disclaimer bar, copyright notice.
- **Disclaimer Banner**: Dismissable homepage notice with localStorage persistence.
- **Trilingual Support**: ES/EN/NAH (Classical Nahuatl) language toggle across all UI components (law content remains Spanish-only).
- **SEO**: JSON-LD (Legislation + WebSite + Organization), dynamic OG images, canonical URLs, alternates, expanded sitemap.
- **Dynamic OG Images**: Per-law opengraph images via Next.js ImageResponse.
- **Homepage**: FeaturedLaws grid, QuickLinks, recently viewed, jurisdiction cards.

## Routes

| Route | Description |
|-------|-------------|
| `/` | Homepage with dashboard, search, and jurisdiction cards |
| `/busqueda` | Advanced law search with filters |
| `/leyes` | Law catalog |
| `/leyes/[id]` | Individual law detail page |
| `/comparar` | Side-by-side law comparison |
| `/categorias` | Browse laws by legal category |
| `/categorias/[category]` | Laws in a specific category |
| `/estados` | Browse laws by Mexican state |
| `/estados/[state]` | Laws in a specific state |
| `/favoritos` | Bookmarked laws |
| `/acerca-de` | About page |
| `/terminos` | Terms & Conditions (trilingual) |
| `/aviso-legal` | Legal Disclaimer (trilingual) |
| `/privacidad` | Privacy Policy (trilingual) |

### Route Redirects

As of Phase 9, all primary routes use Spanish paths. The old English routes (`/search`, `/laws`, `/laws/[id]`, `/compare`) return **301 permanent redirects** to their Spanish equivalents (`/busqueda`, `/leyes`, `/leyes/[id]`, `/comparar`). Existing bookmarks and external links will continue to work.

## Tech Stack
- **Framework**: Next.js 16 (App Router)
- **UI**: React 19, Tailwind CSS 4, @tezca/ui (Shadcn)
- **Search**: Elasticsearch Integration (faceted aggregations)
- **Testing**: Vitest + @testing-library/react (33 test files, 229 tests) + Playwright E2E (8 specs)

## Development

Start the development server from the root of the monorepo:

```bash
npm run dev --workspace=apps/web
```

The portal will be available at [http://localhost:3000](http://localhost:3000).

## Testing

```bash
cd apps/web && npx vitest run
```
