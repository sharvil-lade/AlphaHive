"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "../../lib/utils";
import type { AgentVerdict } from "../../hooks/useChatSession";

// Order verdicts consistently regardless of arrival order.
const ORDER = ["fundamentals", "technical", "news_sentiment", "risk", "bear", "portfolio_doctor"];

function ratingTone(rating?: string | null): string {
  const r = (rating || "").toUpperCase();
  if (/BULL|BUY|LOW|WEAK/.test(r)) return "text-bullish";
  if (/BEAR|SELL|HIGH|STRONG_BEAR|MILD_BEAR/.test(r)) return "text-bearish";
  return "text-mutedText";
}

export function AgentVerdicts({ verdicts }: { verdicts: Record<string, AgentVerdict> }) {
  const [open, setOpen] = useState(false);
  const items = Object.values(verdicts).sort(
    (a, b) => (ORDER.indexOf(a.node) + 100) - (ORDER.indexOf(b.node) + 100)
  );
  if (items.length === 0) return null;

  return (
    <div className="mb-3 rounded-lg border border-surface-border overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 px-3 py-2 text-[12px] text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <span className="font-medium">Analyst views</span>
        <span className="opacity-70">({items.length})</span>
      </button>

      {open && (
        <div className="divide-y divide-surface-border border-t border-surface-border">
          {items.map((v) => (
            <div key={v.node} className="px-3 py-2.5 text-[13px]">
              <div className="flex items-center justify-between gap-2 mb-0.5">
                <span className="font-medium">{v.label}</span>
                {v.rating && (
                  <span className={cn("text-[12px] font-semibold", ratingTone(v.rating))}>
                    {v.rating.replace(/_/g, " ")}
                    {typeof v.confidence === "number" ? ` · ${v.confidence}%` : ""}
                  </span>
                )}
              </div>
              <p className="text-mutedText leading-snug">{v.rationale}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
