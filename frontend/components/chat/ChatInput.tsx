"use client";

import { useRef, useState, KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";
import { cn } from "../../lib/utils";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (content: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-background px-4 py-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-surface-raised border border-surface-border rounded-xl px-3 py-2 focus-within:border-mutedText transition-colors">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={handleKeyDown}
            placeholder={'Ask about a stock, e.g. "Should I buy Reliance right now?"'}
            rows={1}
            disabled={disabled}
            className="flex-1 bg-transparent resize-none text-[15px] placeholder:text-mutedText py-1.5 max-h-40 disabled:opacity-60"
          />
          <button
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className={cn(
              "shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors mb-0.5",
              value.trim() && !disabled
                ? "bg-foreground text-background hover:opacity-90"
                : "bg-surface-hover text-mutedText"
            )}
            aria-label="Send message"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[11px] text-mutedText text-center mt-2">
          AlphaHive can make mistakes. Not financial advice — verify before making investment decisions.
        </p>
      </div>
    </div>
  );
}
