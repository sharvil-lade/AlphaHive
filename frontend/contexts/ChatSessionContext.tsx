"use client";

import { createContext, useContext, ReactNode } from "react";
import { useChatSession } from "../hooks/useChatSession";
import { useToast } from "../components/ui/Toast";

type ChatSessionContextValue = ReturnType<typeof useChatSession>;

const ChatSessionContext = createContext<ChatSessionContextValue | null>(null);

export function ChatSessionProvider({ children }: { children: ReactNode }) {
  const toast = useToast();
  const session = useChatSession((message) => toast(message, "error"));

  return <ChatSessionContext.Provider value={session}>{children}</ChatSessionContext.Provider>;
}

export function useChatSessionContext(): ChatSessionContextValue {
  const ctx = useContext(ChatSessionContext);
  if (!ctx) throw new Error("useChatSessionContext must be used within a ChatSessionProvider");
  return ctx;
}
