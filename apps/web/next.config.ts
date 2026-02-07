import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ['@tezca/ui', '@tezca/lib'],
  async redirects() {
    return [
      { source: '/laws/:path*', destination: '/leyes/:path*', permanent: true },
      { source: '/search', destination: '/busqueda', permanent: true },
      { source: '/compare', destination: '/comparar', permanent: true },
    ];
  },
};

export default nextConfig;
