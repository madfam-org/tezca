/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    transpilePackages: ['@tezca/ui', '@tezca/lib', '@janua/nextjs', '@janua/ui', '@janua/typescript-sdk'],
};

export default nextConfig;
