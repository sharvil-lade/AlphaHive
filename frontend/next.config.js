/** @type {import('next').NextConfig} */

// Session identity is an httpOnly cookie, so the browser must see the API as
// same-origin. Next proxies /svc/api to FastAPI in every environment — 127.0.0.1 when
// running locally, the `backend` service name under Docker Compose — so the browser
// only ever talks to one origin and CORS never enters the picture.
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      // next/font inlines its stylesheet; React injects styles at runtime.
      "style-src 'self' 'unsafe-inline'",
      // 'unsafe-inline' is required by Next's bootstrap script tags.
      "script-src 'self' 'unsafe-inline'" + (process.env.NODE_ENV === 'development' ? " 'unsafe-eval'" : ''),
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
];

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Emits .next/standalone, which the Dockerfile's runner stage copies.
  output: 'standalone',

  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },

  async rewrites() {
    return [{ source: '/svc/api/:path*', destination: `${BACKEND_URL}/:path*` }];
  },
};

module.exports = nextConfig;
