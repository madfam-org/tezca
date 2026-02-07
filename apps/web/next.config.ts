import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ['@tezca/ui', '@tezca/lib'],
};

export default nextConfig;
