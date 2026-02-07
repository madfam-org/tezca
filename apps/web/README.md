# Public Portal (Web)

The citizen-facing web application for searching and reading Mexican laws.

## Features
- **Law Search**: Full-text search with filters (Federal, State, Date) and autocomplete typeahead.
- **Law Visualization**: Clean, readable presentation of laws with indices.
- **Comparison**: Side-by-side law comparison with sync scroll, metadata panel, and mobile tabs.
- **Dashboard**: High-level statistics of the legal database.
- **Legal Pages**: Terms & Conditions, Legal Disclaimer, Privacy Policy — bilingual ES/EN.
- **Site Footer**: Navigation links, official sources, disclaimer bar, copyright notice.
- **Disclaimer Banner**: Dismissable homepage notice with localStorage persistence.
- **Bilingual Support**: ES/EN language toggle for legal pages and footer (law content remains Spanish-only).

## Routes

| Route | Description |
|-------|-------------|
| `/` | Homepage with dashboard, search, and jurisdiction cards |
| `/search` | Advanced law search with filters |
| `/laws` | Law catalog |
| `/laws/[id]` | Individual law detail page |
| `/compare` | Side-by-side law comparison |
| `/terminos` | Terms & Conditions (bilingual) |
| `/aviso-legal` | Legal Disclaimer (bilingual) |
| `/privacidad` | Privacy Policy (bilingual) |

## Tech Stack
- **Framework**: Next.js 15 (App Router)
- **UI**: React 19, Tailwind CSS 4, @tezca/ui (Shadcn)
- **Search**: Elasticsearch Integration
- **Testing**: Vitest + @testing-library/react (13 test files, 82 tests)

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
