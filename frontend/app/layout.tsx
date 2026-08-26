import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import React from "react";
import { Providers } from "./providers";
import { ThemeProvider } from "./theme-provider";
import { ToastProvider } from "../components/ui/Toast";
import { AuthProvider } from "../contexts/AuthContext";
import { AppShell } from "../components/layout/AppShell";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://alphahive.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Alpha Hive — AI stock research for Indian & global markets",
    template: "%s · Alpha Hive",
  },
  description:
    "Ask about any Indian or global stock in plain English. A hive of specialist AI agents researches fundamentals, technicals, news sentiment, risk and the bear case, then gives you one clear answer.",
  keywords: ["stock research", "AI stock analysis", "NSE", "BSE", "Indian stock market", "portfolio analysis"],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Alpha Hive",
    title: "Alpha Hive — AI stock research for Indian & global markets",
    description:
      "A team of specialist AI agents researches every angle of a stock, then hands you a clear, reasoned answer.",
    images: [{ url: "/logo.png", width: 512, height: 512, alt: "Alpha Hive" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Alpha Hive — AI stock research",
    description: "A hive of specialist AI agents researches any stock and gives you one clear answer.",
    images: ["/logo.png"],
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`h-full ${geistSans.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <body className="antialiased min-h-screen bg-background text-foreground font-sans">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:rounded-md focus:bg-surface-raised focus:px-3 focus:py-2 focus:text-sm focus:ring-2 focus:ring-foreground"
        >
          Skip to content
        </a>
        <ThemeProvider>
          <Providers>
            <ToastProvider>
              <AuthProvider>
                <AppShell>{children}</AppShell>
              </AuthProvider>
            </ToastProvider>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
