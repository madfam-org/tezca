/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    transpilePackages: ['@tezca/ui', '@tezca/lib'],
};

export default nextConfig;
