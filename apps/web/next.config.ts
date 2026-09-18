import type { NextConfig } from 'next';
const config: NextConfig = {
  transpilePackages: ['@ugc/contracts', '@ugc/ui'],
  poweredByHeader: false,
  agentRules: false,
  // Uploads go through the /api rewrite; the default 10MB buffer cut videos off mid-upload
  // (API socket hang up). Match the API's 500MB video limit plus multipart overhead.
  experimental: { proxyTimeout: 330_000, proxyClientMaxBodySize: '520mb' },
  async rewrites() {
    return [{source: '/api/:path*', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/:path*`}];
  },
};
export default config;
