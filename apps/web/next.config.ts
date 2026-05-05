import type { NextConfig } from "next";

// Selva Atrium iframe allowance.
// The Atrium is the consumer-side feature in selva-office that surfaces every MADFAM
// platform as a window into a single welcoming central space. To let the Atrium
// embed tezca.mx pages, we permit selva.town as a frame-ancestor. X-Frame-Options:
// SAMEORIGIN remains as a legacy fallback for browsers that don't honor CSP
// frame-ancestors. App-wide; auth surfaces (`/login`, `/api/auth/*`) inherit the
// same policy. Acceptable because Innovaciones MADFAM runs both Selva and Tezca.
const SELVA_FRAME_ANCESTORS =
  "frame-ancestors 'self' https://selva.town https://*.selva.town https://*.madfam.io";

const nextConfig: NextConfig = {
  output: process.env.NEXT_BUILD_STANDALONE === 'false' ? undefined : "standalone",
  transpilePackages: ['@tezca/ui', '@tezca/lib', '@janua/ui', '@janua/nextjs'],
  async redirects() {
    return [
      { source: '/laws/:path*', destination: '/leyes/:path*', permanent: true },
      { source: '/search', destination: '/busqueda', permanent: true },
      { source: '/compare', destination: '/comparar', permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'Content-Security-Policy', value: SELVA_FRAME_ANCESTORS },
        ],
      },
    ];
  },
};

export default nextConfig;
