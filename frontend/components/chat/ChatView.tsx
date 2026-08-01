"use client";

import { useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { useChatSessionContext } from "../../contexts/ChatSessionContext";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ThemeToggle } from "../layout/ThemeToggle";

const SUGGESTIONS = [
  "Should I buy Reliance right now?",
  "Analyze my portfolio",
  "What's the technical outlook for TCS?",
  "Am I too concentrated in any sector?",
];

export function ChatView() {
  const { conversationId, messages, isSending, sendMessage, loadConversation } = useChatSessionContext();
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  // useParams (not useSearchParams) — reads the already-known route segment, so
  // unlike search params it needs no Suspense boundary (the cause of the earlier
  // Recents-routing crash this app had reverted).
  const params = useParams();
  const urlConversationId = typeof params.conversationId === "string" ? params.conversationId : null;

  // URL -> state: a deep link / refresh at /chat/{id}, or a Sidebar "Recents"
  // click, loads that conversation into the shared session context.
  useEffect(() => {
    if (urlConversationId && urlConversationId !== conversationId) {
      loadConversation(urlConversationId).catch(() => router.replace("/"));
    }
  }, [urlConversationId]);

  // state -> URL: once a conversation exists (e.g. right after the first message
  // creates one), reflect its id in the route, ChatGPT-style. `replace` (not
  // `push`) so this sync never adds noisy extra history entries.
  useEffect(() => {
    if (conversationId && conversationId !== urlConversationId) {
      router.replace(`/chat/${conversationId}`);
    } else if (!conversationId && urlConversationId) {
      router.replace("/");
    }
  }, [conversationId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <header className="h-14 shrink-0 border-b border-surface-border flex items-center justify-end px-4">
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
                Ask about any Indian or global stock — I'll run fundamentals, technical, sentiment, and
                risk analysis, then give you a straight answer. Add your portfolio and I'll factor in
                what you already own.
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
            messages.map((m) => <MessageBubble key={m.id} message={m} />)
          )}
        </div>
      </div>

      <ChatInput onSend={sendMessage} disabled={isSending} />
    </div>
  );
}
