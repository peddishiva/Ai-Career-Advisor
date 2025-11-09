/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['images.unsplash.com', 'avatars.githubusercontent.com'],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
    unoptimized: process.env.NODE_ENV !== 'production', // Only optimize in production
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // Vercel handles output automatically
  // Disable source maps for faster builds
  productionBrowserSourceMaps: false,
  // Configure build output
  distDir: '.next',
  generateBuildId: async () => {
    return process.env.VERCEL_GIT_COMMIT_SHA || 'build';
  },
  // Enable compression
  compress: true,
  // Enable HTTP/2
  httpAgentOptions: {
    keepAlive: true,
  },
  // Enable webpack optimizations
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Don't include certain modules in the client build
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
