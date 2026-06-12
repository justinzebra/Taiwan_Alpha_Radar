/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output keeps the production Docker image small.
  output: "standalone",
  // Don't fail the production build on lint warnings (TS type-checking still runs).
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
