# Admin Console

The administrative dashboard for operating the Leyes Como Código ingestion pipeline.

## Features
- **Job Monitoring**: Real-time status of scraping and processing jobs.
- **Ingestion Control**: Trigger new ingestion runs (All Laws or High Priority).
- **System Stats**: View database statistics and health metrics.

## Tech Stack
- **Framework**: Next.js 16 (App Router)
- **UI**: React 19, Tailwind CSS, @leyesmx/ui (Shadcn)
- **State**: React Hooks for polling and data fetching

## Development

Start the development server from the root of the monorepo:

```bash
npm run dev --workspace=apps/admin
```

The console will be available at [http://localhost:3001](http://localhost:3001).
