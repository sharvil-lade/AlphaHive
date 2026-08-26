"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { Check, Copy, Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { AgentTracePanel } from "./AgentTracePanel";
import { AgentVerdicts } from "./AgentVerdicts";
import type { ChatMessage } from "../../hooks/useChatSession";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard is unavailable outside a secure context; nothing useful to do.
    }
  };

  return (
    <button
      onClick={copy}
      aria-label={copied ? "Copied" : "Copy answer"}
      title={copied ? "Copied" : "Copy answer"}
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-bullish" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-[85%] sm:max-w-[75%] bg-surface-raised border border-surface-border rounded-lg px-4 py-2.5 text-[15px] whitespace-pre-wrap break-words">
          {message.content}
        </div>
      </div>
    );
  }

  const isThinking = message.status === "pending" || (message.status === "running" && !message.content);

  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-full sm:max-w-[85%] w-full min-w-0">
        <AgentTracePanel traces={message.traces} />
        <AgentVerdicts verdicts={message.verdicts} />

        {isThinking ? (
          <div className="flex items-center gap-2 text-mutedText text-sm py-1">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Thinking...
          </div>
        ) : (
          <>
            <div className={cn("chat-prose", message.status === "failed" && "text-bearish")}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: false }]]}
                rehypePlugins={[rehypeKatex]}
              >
                {message.content}
              </ReactMarkdown>
            </div>

            {message.status !== "running" && message.content && (
              <div className="flex items-center gap-1 -ml-2 mt-1">
                <CopyButton text={message.content} />
                {message.status === "cancelled" && (
                  <span className="text-[12px] text-mutedText px-1">Stopped</span>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
