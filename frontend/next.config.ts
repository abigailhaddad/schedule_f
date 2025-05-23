import type { NextConfig } from "next";

const isDevelopment = process.env.NODE_ENV === 'development';

const nextConfig: NextConfig = {
  staticPageGenerationTimeout: 120, // 2 minutes max per page, can be increased if needed
  
  // Recommended: Configure image optimization if you use next/image
  images: {
    formats: ['image/webp'], // Optimize to modern formats
    minimumCacheTTL: 60 * 60 * 24 * 7, // Cache optimized images for 1 week
  },
  
  // For faster development iteration, you can ignore these during dev
  typescript: {
    ignoreBuildErrors: isDevelopment,
  },
  eslint: {
    ignoreDuringBuilds: isDevelopment,
  },
};

export default nextConfig;
