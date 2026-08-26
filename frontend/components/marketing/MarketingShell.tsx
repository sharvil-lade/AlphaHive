import Link from "next/link";
import { ReactNode } from "react";
import { ThemeToggle } from "../layout/ThemeToggle";

export function MarketingShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 h-14 shrink-0 border-b border-surface-border bg-background/80 backdrop-blur">
        <div className="max-w-5xl mx-auto h-full px-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- plain <img> keeps the brand PNG un-optimized/crisp */}
            <img src="/logo.png" alt="" width={24} height={24} className="w-6 h-6 rounded-md" />
            <span className="text-sm font-semibold tracking-tight">Alpha Hive</span>
          </Link>
          <nav className="flex items-center gap-1" aria-label="Site">
            <Link
              href="/#how-it-works"
              className="hidden sm:inline-flex px-3 py-1.5 rounded-md text-sm text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
            >
              How it works
            </Link>
            <Link
              href="/login"
              className="px-3 py-1.5 rounded-md text-sm text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/chat"
              className="ml-1 inline-flex items-center rounded-md bg-foreground text-background px-3 py-1.5 text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Try free
            </Link>
            <ThemeToggle className="ml-1" />
          </nav>
        </div>
      </header>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-surface-border">
        <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
          <p className="text-[12px] text-mutedText leading-relaxed max-w-3xl">
            Alpha Hive provides educational research and analysis only. It is not investment advice
            and not a substitute for a SEBI-registered investment adviser. Markets carry risk; you
            are responsible for your own decisions. Always verify independently before you invest.
          </p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px] text-mutedText">
            <span>© {new Date().getFullYear()} Alpha Hive</span>
            <Link href="/privacy" className="hover:text-foreground transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-foreground transition-colors">
              Terms
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
