'use client';

import dynamic from 'next/dynamic';

// LawGraphContainer pulls in Sigma + graphology + the force-atlas-2 worker —
// DOM-bound canvas rendering that can never run on the server. Next.js
// requires `ssr: false` dynamics to live inside a Client Component, and the
// /grafo page must stay a Server Component (it exports `metadata`), so the
// deferral lives here.
export const LawGraphClient = dynamic(
    () =>
        import('@/components/graph/LawGraphContainer').then(m => ({
            default: m.LawGraphContainer,
        })),
    { ssr: false },
);
