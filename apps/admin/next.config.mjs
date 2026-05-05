// Selva Atrium iframe allowance — see apps/web/next.config.ts for the full rationale.
// Tezca admin is internal-only (Janua SSO gated), surfacing it inside the Atrium does
// not relax any third-party trust boundary.
const SELVA_FRAME_ANCESTORS =
    "frame-ancestors 'self' https://selva.town https://*.selva.town https://*.madfam.io";

/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    transpilePackages: ['@tezca/ui', '@tezca/lib', '@janua/nextjs', '@janua/ui', '@janua/typescript-sdk'],
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
