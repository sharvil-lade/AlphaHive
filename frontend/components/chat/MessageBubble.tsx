"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { AgentTracePanel } from "./AgentTracePanel";
import { AgentVerdicts } from "./AgentVerdicts";
import type { ChatMessage } from "../../hooks/useChatSession";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-[75%] bg-surface-raised border border-surface-border rounded-lg px-4 py-2.5 text-[15px] whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  const isThinking = message.status === "pending" || (message.status === "running" && !message.content);

  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-[85%] w-full">
        <AgentTracePanel traces={message.traces} />
        <AgentVerdicts verdicts={message.verdicts} />

        {isThinking ? (
          <div className="flex items-center gap-2 text-mutedText text-sm py-1">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Thinking...
          </div>
        ) : (
          <div className={cn("chat-prose", message.status === "failed" && "text-bearish")}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: false }]]}
              rehypePlugins={[rehypeKatex]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
