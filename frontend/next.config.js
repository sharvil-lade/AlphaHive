/** @type {import('next').NextConfig} */

// Session identity is an httpOnly cookie, so the browser must see the API as
// same-origin. Vercel Services already routes /svc/api to FastAPI; in local dev we
// proxy it here so dev and prod behave identically and CORS never enters the picture.
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

  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },

  async rewrites() {
    // In production the platform owns this route; only proxy when running locally.
    if (process.env.NODE_ENV !== 'development') return [];
    return [{ source: '/svc/api/:path*', destination: `${BACKEND_URL}/:path*` }];
  },
};

module.exports = nextConfig;
