"use client";

import { useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { RefreshCw, Sparkles } from "lucide-react";
import { useChatSessionContext } from "../../contexts/ChatSessionContext";
import { useAuth } from "../../contexts/AuthContext";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ThemeToggle } from "../layout/ThemeToggle";
import Link from "next/link";

const SUGGESTIONS = [
  "Should I buy Reliance right now?",
  "Analyze my portfolio",
  "What's the technical outlook for TCS?",
  "Am I too concentrated in any sector?",
];

export function ChatView() {
  const { conversationId, messages, isSending, streamingId, sendMessage, stopMessage, regenerate, loadConversation } =
    useChatSessionContext();
  const { session } = useAuth();
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const params = useParams();
  const urlConversationId = typeof params.conversationId === "string" ? params.conversationId : null;

  // URL -> state: a deep link or a Recents click loads that conversation.
  // Keyed on the URL alone on purpose: including `conversationId` would re-fire the
  // moment loadConversation sets it, reloading the conversation in a loop.
  useEffect(() => {
    if (urlConversationId && urlConversationId !== conversationId) {
      loadConversation(urlConversationId).catch(() => router.replace("/chat"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlConversationId]);

  // state -> URL: reflect a newly created conversation in the route, ChatGPT-style.
  // Mirror of the effect above — keyed on state alone so the two never chase
  // each other. `replace` (not `push`) keeps it out of the history stack.
  useEffect(() => {
    if (conversationId && conversationId !== urlConversationId) {
      router.replace(`/chat/${conversationId}`);
    } else if (!conversationId && urlConversationId) {
      router.replace("/chat");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const lastMessage = messages[messages.length - 1];
  const canRegenerate =
    !isSending &&
    lastMessage?.role === "assistant" &&
    ["completed", "failed", "cancelled"].includes(lastMessage.status);

  return (
    <div className="flex flex-col h-full">
      {/* pl-14 clears the fixed mobile menu button rendered by the Sidebar. */}
      <header className="h-14 shrink-0 border-b border-surface-border flex items-center justify-end gap-2 pl-14 pr-4 md:pl-4">
        {!session?.authenticated && (
          <Link
            href="/signup"
            className="text-[12px] text-mutedText hover:text-foreground transition-colors mr-auto md:mr-0"
          >
            Sign up to save your history
          </Link>
        )}
        <ThemeToggle />
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-6">
        <div className="max-w-3xl mx-auto w-full">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[50vh] text-center">
              <div className="w-10 h-10 rounded-full bg-surface-raised border border-surface-border flex items-center justify-center mb-4">
                <Sparkles className="w-5 h-5 text-mutedText" />
              </div>
              <h1 className="text-xl font-semibold mb-1.5">What stock are you researching?</h1>
              <p className="text-sm text-mutedText mb-6 max-w-md">
                Ask about any Indian or global stock — I&apos;ll run fundamentals, technical,
                sentiment and risk analysis, then give you a straight answer. Add your portfolio and
                I&apos;ll factor in what you already own.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="text-left text-sm px-3.5 py-2.5 rounded-lg border border-surface-border hover:bg-surface-hover transition-colors text-mutedText hover:text-foreground"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Screen readers get told when an answer finishes, rather than silently
                  receiving a wall of streamed text. */}
              <div aria-live="polite" className="sr-only">
                {streamingId ? "Analyzing…" : lastMessage?.role === "assistant" ? "Answer ready." : ""}
              </div>

              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}

              {canRegenerate && (
                <div className="flex justify-start mb-6">
                  <button
                    onClick={regenerate}
                    className="inline-flex items-center gap-1.5 rounded-md border border-surface-border px-2.5 py-1.5 text-[12px] text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Regenerate
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <ChatInput onSend={sendMessage} onStop={stopMessage} isStreaming={!!streamingId} disabled={isSending} />
    </div>
  );
}
