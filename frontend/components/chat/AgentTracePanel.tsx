"use client";

import { Loader2, CheckCircle2, XCircle, Circle } from "lucide-react";
import { cn } from "../../lib/utils";
import type { AgentStatus } from "../../hooks/useChatSession";

// Node keys MUST match the SSE `node` values emitted by the backend chat graph
// (app/agents/chat_nodes.py + graph.py). Master-slave topology: the supervisor
// plans, the specialist slaves run, then synthesis writes the decision.
const PIPELINE = [
  { key: "supervisor", label: "Planning" },
  { key: "fundamentals", label: "Fundamentals" },
  { key: "technical", label: "Technical" },
  { key: "news_sentiment", label: "News & Sentiment" },
  { key: "risk", label: "Risk" },
  { key: "bear", label: "Bear Case" },
  { key: "portfolio_doctor", label: "Portfolio Doctor" },
  { key: "synthesis", label: "Synthesizing" },
];

function StatusIcon({ status }: { status?: AgentStatus }) {
  if (status === "running") return <Loader2 className="w-3 h-3 animate-spin text-mutedText" />;
  if (status === "completed") return <CheckCircle2 className="w-3 h-3 text-bullish" />;
  if (status === "failed") return <XCircle className="w-3 h-3 text-bearish" />;
  return <Circle className="w-3 h-3 text-surface-border" />;
}

export function AgentTracePanel({ traces }: { traces: Record<string, AgentStatus> }) {
  const activeNodes = PIPELINE.filter((n) => traces[n.key] !== undefined);
  if (activeNodes.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mb-3">
      {activeNodes.map((node) => {
        const status = traces[node.key];
        return (
          <div
            key={node.key}
            className={cn(
              "flex items-center gap-1.5 px-2 py-1 rounded-full border text-[12px] transition-colors",
              status === "completed" && "border-surface-border text-mutedText",
              status === "running" && "border-surface-border text-foreground bg-surface-hover",
              status === "failed" && "border-bearish/30 text-bearish"
            )}
          >
            <StatusIcon status={status} />
            {node.label}
          </div>
        );
      })}
    </div>
  );
}
