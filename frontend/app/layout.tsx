import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import React from "react";
import { Providers } from "./providers";
import { ThemeProvider } from "./theme-provider";
import { Sidebar } from "../components/layout/Sidebar";
import { ChatSessionProvider } from "../contexts/ChatSessionContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AlphaHive",
  description: "AI-powered stock market research and analysis chat, focused on Indian and global equities.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`h-full ${geistSans.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <body className="antialiased h-screen bg-background text-foreground font-sans flex overflow-hidden">
        <ThemeProvider>
          <Providers>
            <ChatSessionProvider>
              <Sidebar />
              <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
            </ChatSessionProvider>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
