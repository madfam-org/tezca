# Public Portal (Web)

The citizen-facing web application for searching and reading Mexican laws.

## Features
- **Law Search**: Full-text search with filters (Federal, State, Date).
- **Law Visualization**: Clean, readable presentation of laws with indices.
- **Comparison**: Compare different versions of laws (Coming Soon).
- **Dashboard**: High-level statistics of the legal database.

## Tech Stack
- **Framework**: Next.js 15 (App Router)
- **UI**: React 19, Tailwind CSS, @leyesmx/ui (Shadcn)
- **Search**: Elasticsearch Integration

## Development

Start the development server from the root of the monorepo:

```bash
npm run dev --workspace=apps/web
```

The portal will be available at [http://localhost:3000](http://localhost:3000).
