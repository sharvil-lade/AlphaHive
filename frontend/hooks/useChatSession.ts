"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createConversation,
  fetchConversationDetail,
  fetchConversations,
  getChatStreamUrl,
  postChatMessage,
} from "../services/api";

export type AgentStatus = "running" | "completed" | "failed";
export type MessageStatus = "pending" | "running" | "completed" | "failed";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: MessageStatus;
  traces: Record<string, AgentStatus>;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  updated_at: string;
}

export function useChatSession(sessionId: string) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const refreshConversations = useCallback(async () => {
    if (!sessionId) return;
    try {
      const list = await fetchConversations(sessionId);
      setConversations(list);
    } catch {
      // Recents list is a nice-to-have — a transient fetch failure shouldn't break chat.
    }
  }, [sessionId]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const ensureConversation = useCallback(async () => {
    if (conversationId) return conversationId;
    const conv = await createConversation(sessionId);
    setConversationId(conv.id);
    return conv.id as string;
  }, [conversationId, sessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || !sessionId) return;

      setIsSending(true);
      try {
        const convId = await ensureConversation();

        const localUserId = `local-user-${Date.now()}`;
        const localAssistantId = `local-assistant-${Date.now()}`;

        setMessages((prev) => [
          ...prev,
          { id: localUserId, role: "user", content: trimmed, status: "completed", traces: {} },
          { id: localAssistantId, role: "assistant", content: "", status: "pending", traces: {} },
        ]);

        const res = await postChatMessage(convId, trimmed);
        const assistantId: string = res.assistant_message.id;

        setMessages((prev) =>
          prev.map((m) => (m.id === localAssistantId ? { ...m, id: assistantId, status: "running" } : m))
        );
        refreshConversations();

        await new Promise<void>((resolve) => {
          const es = new EventSource(getChatStreamUrl(assistantId));
          eventSourceRef.current = es;

          es.onmessage = (event) => {
            let data: any;
            try {
              data = JSON.parse(event.data);
            } catch {
              return;
            }

            if (data.type === "agent-status") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, traces: { ...m.traces, [data.node]: data.status } } : m
                )
              );
            } else if (data.type === "text-delta") {
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + data.delta } : m))
              );
            } else if (data.type === "done") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: data.content || m.content, status: data.status }
                    : m
                )
              );
              es.close();
              eventSourceRef.current = null;
              resolve();
            }
          };

          es.onerror = () => {
            es.close();
            eventSourceRef.current = null;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId && m.status !== "completed" ? { ...m, status: "failed" } : m))
            );
            resolve();
          };
        });
      } finally {
        setIsSending(false);
      }
    },
    [ensureConversation, sessionId, refreshConversations]
  );

  const loadConversation = useCallback(async (id: string) => {
    const detail = await fetchConversationDetail(id);
    setConversationId(detail.id);
    setMessages(
      detail.messages.map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        status: m.status,
        traces: Object.fromEntries((m.traces || []).map((t: any) => [t.node, t.status])),
      }))
    );
  }, []);

  const startNewConversation = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setConversationId(null);
    setMessages([]);
  }, []);

  return {
    conversationId,
    messages,
    isSending,
    conversations,
    sendMessage,
    loadConversation,
    startNewConversation,
    refreshConversations,
  };
}
