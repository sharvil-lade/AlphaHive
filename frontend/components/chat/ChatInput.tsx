"use client";

import { useRef, useState, KeyboardEvent } from "react";
import { ArrowUp, Square } from "lucide-react";
import { cn } from "../../lib/utils";

const MAX_CHARS = 4000;

export function ChatInput({
  onSend,
  onStop,
  isStreaming,
  disabled,
}: {
  onSend: (content: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
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

  const overLimit = value.length > MAX_CHARS;

  return (
    <div className="bg-background px-4 py-4">
      <div className="max-w-3xl mx-auto">
        <div
          className={cn(
            "flex items-end gap-2 bg-surface-raised border rounded-xl px-3 py-2 transition-colors",
            overLimit ? "border-bearish" : "border-surface-border focus-within:border-mutedText"
          )}
        >
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
            aria-label="Your question"
            className="flex-1 bg-transparent resize-none text-[15px] placeholder:text-mutedText py-1.5 max-h-40 disabled:opacity-60 focus-visible:ring-0 focus-visible:ring-offset-0"
          />

          {isStreaming ? (
            <button
              onClick={onStop}
              aria-label="Stop generating"
              title="Stop generating"
              className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center mb-0.5 border border-surface-border text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
            >
              <Square className="w-3 h-3 fill-current" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={disabled || !value.trim() || overLimit}
              aria-label="Send message"
              className={cn(
                "shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors mb-0.5",
                value.trim() && !disabled && !overLimit
                  ? "bg-foreground text-background hover:opacity-90"
                  : "bg-surface-hover text-mutedText"
              )}
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          )}
        </div>

        {overLimit && (
          <p role="alert" className="text-[11px] text-bearish text-center mt-1.5">
            {value.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters — please shorten your question.
          </p>
        )}

        <p className="text-[11px] text-mutedText text-center mt-2">
          Alpha Hive is an AI research assistant, not a SEBI-registered investment adviser. Its
          output is for information only — not investment advice. Verify independently before you
          invest.
        </p>
      </div>
    </div>
  );
}
