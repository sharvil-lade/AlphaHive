import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://alphahive.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Signed-in surfaces hold user data and have nothing to index.
      disallow: ["/chat", "/portfolio", "/account", "/login", "/svc/"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
