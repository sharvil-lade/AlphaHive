import Link from "next/link";
import { ArrowRight, Bug, Check, LineChart, Newspaper, ShieldAlert, Stethoscope } from "lucide-react";
import { MarketingShell } from "../components/marketing/MarketingShell";

const AGENTS = [
  { icon: LineChart, name: "Fundamentals", blurb: "Valuation, profitability and the actual business behind the ticker." },
  { icon: LineChart, name: "Technical", blurb: "Trend, momentum, support and resistance from live price data." },
  { icon: Newspaper, name: "News & Sentiment", blurb: "What the market is saying right now, and how loudly." },
  { icon: ShieldAlert, name: "Risk", blurb: "Volatility, beta, drawdown and the filings nobody reads." },
  { icon: Bug, name: "Bear Case", blurb: "A dedicated red-team that argues against every buy." },
  { icon: Stethoscope, name: "Portfolio Doctor", blurb: "Concentration, sector gaps and what to rebalance." },
];

const FEATURES = [
  "Six specialist agents, not one opinion",
  "Watch every agent reason in real time",
  "Indian markets first — proper NSE & BSE coverage",
  "Import your Groww holdings in one click",
  "Every answer shows its sources and its dissent",
  "Free to try, no card required",
];

const QUESTIONS = [
  "Should I buy Reliance right now?",
  "Am I too concentrated in any one sector?",
  "What's the technical outlook for TCS?",
  "Is Infosys a good long-term hold?",
];

export default function LandingPage() {
  return (
    <MarketingShell>
      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-20 pb-16 text-center">
        <p className="inline-flex items-center gap-1.5 rounded-full border border-surface-border px-3 py-1 text-[12px] text-mutedText mb-6">
          🐝 A hive of AI analysts, not a single chatbot
        </p>
        <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight leading-tight mb-5">
          Your AI research hive for the stock market
        </h1>
        <p className="text-base sm:text-lg text-mutedText leading-relaxed mb-8 max-w-2xl mx-auto">
          Ask about any Indian or global stock in plain English. A team of specialist agents
          studies the fundamentals, the charts, the news mood, the risk and the bear case — then
          hands you one clear, reasoned answer.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/chat"
            className="inline-flex items-center justify-center gap-1.5 rounded-md bg-foreground text-background px-5 py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Start researching free <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/signup"
            className="inline-flex items-center justify-center rounded-md border border-surface-border px-5 py-2.5 text-sm font-medium hover:bg-surface-hover transition-colors"
          >
            Create an account
          </Link>
        </div>
        <p className="text-[12px] text-mutedText mt-4">
          No card, no signup needed to try. Create an account to keep your history.
        </p>
      </section>

      {/* Sample questions */}
      <section className="max-w-3xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {QUESTIONS.map((q) => (
            <Link
              key={q}
              href="/chat"
              className="text-left text-sm px-4 py-3 rounded-lg border border-surface-border text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
            >
              “{q}”
            </Link>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-surface-border bg-surface">
        <div className="max-w-5xl mx-auto px-6 py-20">
          <h2 className="text-2xl font-semibold tracking-tight text-center mb-3">Meet the hive</h2>
          <p className="text-sm text-mutedText text-center max-w-xl mx-auto mb-12">
            A supervisor plans the work and dispatches the specialists it needs. They research in
            parallel, then a lead agent weighs every view — including where they disagree — and
            writes the answer.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {AGENTS.map(({ icon: Icon, name, blurb }) => (
              <div key={name} className="rounded-lg border border-surface-border bg-surface-raised p-4">
                <Icon className="w-4 h-4 text-mutedText mb-2.5" strokeWidth={1.75} />
                <h3 className="text-sm font-medium mb-1">{name}</h3>
                <p className="text-[13px] text-mutedText leading-relaxed">{blurb}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl font-semibold tracking-tight text-center mb-12">
          Research you can actually audit
        </h2>
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 max-w-3xl mx-auto">
          {FEATURES.map((f) => (
            <li key={f} className="flex items-start gap-2.5 text-sm">
              <Check className="w-4 h-4 text-bullish shrink-0 mt-0.5" strokeWidth={2} />
              <span className="text-mutedText">{f}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* CTA */}
      <section className="border-t border-surface-border">
        <div className="max-w-2xl mx-auto px-6 py-20 text-center">
          <h2 className="text-2xl font-semibold tracking-tight mb-3">Ask it something</h2>
          <p className="text-sm text-mutedText mb-7">
            Pick a stock you already own an opinion about, and see whether the hive agrees.
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center justify-center gap-1.5 rounded-md bg-foreground text-background px-5 py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Open Alpha Hive <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </MarketingShell>
  );
}
