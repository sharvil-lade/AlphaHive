"use client";

import { createContext, useContext, ReactNode } from "react";
import { useSessionId } from "../hooks/useSessionId";
import { useChatSession } from "../hooks/useChatSession";

type ChatSessionContextValue = ReturnType<typeof useChatSession> & { sessionId: string };

const ChatSessionContext = createContext<ChatSessionContextValue | null>(null);

export function ChatSessionProvider({ children }: { children: ReactNode }) {
  const sessionId = useSessionId();
  const session = useChatSession(sessionId);

  return (
    <ChatSessionContext.Provider value={{ sessionId, ...session }}>{children}</ChatSessionContext.Provider>
  );
}

export function useChatSessionContext(): ChatSessionContextValue {
  const ctx = useContext(ChatSessionContext);
  if (!ctx) throw new Error("useChatSessionContext must be used within a ChatSessionProvider");
  return ctx;
}
