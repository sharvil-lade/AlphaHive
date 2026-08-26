"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../services/api";
import { ApiError } from "../services/api";
import type { Conversation, MessageRecord } from "../services/api";

export type AgentStatus = "running" | "completed" | "failed";
export type MessageStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface AgentVerdict {
  node: string;
  label: string;
  rating?: string | null;
  confidence?: number | null;
  rationale: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: MessageStatus;
  traces: Record<string, AgentStatus>;
  verdicts: Record<string, AgentVerdict>;
}

export type ConversationSummary = Conversation;

/** Persisted traces carry the verdict now, so "Analyst views" survives a reload. */
function hydrate(m: MessageRecord): ChatMessage {
  const traces: Record<string, AgentStatus> = {};
  const verdicts: Record<string, AgentVerdict> = {};
  for (const t of m.traces || []) {
    traces[t.node] = t.status;
    if (t.rating || t.summary) {
      verdicts[t.node] = {
        node: t.node,
        label: t.label || t.node,
        rating: t.rating,
        confidence: t.confidence,
        rationale: t.summary || "",
      };
    }
  }
  return { id: m.id, role: m.role, content: m.content, status: m.status, traces, verdicts };
}

export function useChatSession(onError?: (message: string) => void) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const fail = useCallback(
    (e: unknown, fallback: string) => {
      onError?.(e instanceof ApiError ? e.message : fallback);
    },
    [onError]
  );

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.fetchConversations());
    } catch {
      // The Recents list is a nice-to-have; a transient failure shouldn't break chat.
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const patch = useCallback((id: string, update: Partial<ChatMessage>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...update } : m)));
  }, []);

  /** Consume the SSE stream for one assistant message until its terminal event. */
  const consumeStream = useCallback(
    (assistantId: string, fromIndex = 0) =>
      new Promise<void>((resolve) => {
        let seen = fromIndex;
        let retried = false;

        const open = (startAt: number) => {
          const es = new EventSource(api.getChatStreamUrl(assistantId, startAt));
          eventSourceRef.current = es;

          const finish = () => {
            es.close();
            eventSourceRef.current = null;
            setStreamingId(null);
            resolve();
          };

          es.onmessage = (event) => {
            seen += 1;
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
            } else if (data.type === "agent-verdict") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        verdicts: {
                          ...m.verdicts,
                          [data.node]: {
                            node: data.node,
                            label: data.label,
                            rating: data.rating,
                            confidence: data.confidence,
                            rationale: data.rationale,
                          },
                        },
                      }
                    : m
                )
              );
            } else if (data.type === "text-delta") {
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + data.delta } : m))
              );
            } else if (data.type === "done") {
              patch(assistantId, { content: data.content || undefined, status: data.status });
              finish();
            }
          };

          es.onerror = () => {
            es.close();
            eventSourceRef.current = null;
            // One reconnect from where we left off — `from_index` stops the server
            // replaying deltas we already applied and doubling the text.
            if (!retried) {
              retried = true;
              open(seen);
              return;
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId && m.status !== "completed"
                  ? { ...m, status: "failed", content: m.content || "The connection dropped. Please try again." }
                  : m
              )
            );
            setStreamingId(null);
            resolve();
          };
        };

        open(fromIndex);
      }),
    [patch]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isSending) return;

      setIsSending(true);
      const localUserId = `local-user-${Date.now()}`;
      const localAssistantId = `local-assistant-${Date.now()}`;

      try {
        let convId = conversationId;
        if (!convId) {
          convId = (await api.createConversation()).id;
          setConversationId(convId);
        }

        setMessages((prev) => [
          ...prev,
          { id: localUserId, role: "user", content: trimmed, status: "completed", traces: {}, verdicts: {} },
          { id: localAssistantId, role: "assistant", content: "", status: "pending", traces: {}, verdicts: {} },
        ]);

        const res = await api.postChatMessage(convId, trimmed);
        const assistantId = res.assistant_message.id;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === localAssistantId
              ? { ...m, id: assistantId, status: "running" }
              : m.id === localUserId
                ? { ...m, id: res.user_message.id }
                : m
          )
        );
        setStreamingId(assistantId);
        refreshConversations();

        await consumeStream(assistantId);
      } catch (e) {
        // Drop the optimistic pair so the transcript never shows a request that
        // was never accepted by the server.
        setMessages((prev) => prev.filter((m) => m.id !== localUserId && m.id !== localAssistantId));
        fail(e, "Couldn't send that message.");
      } finally {
        setIsSending(false);
      }
    },
    [conversationId, consumeStream, isSending, refreshConversations, fail]
  );

  const stopMessage = useCallback(async () => {
    if (!streamingId) return;
    try {
      await api.stopChatMessage(streamingId);
    } catch (e) {
      fail(e, "Couldn't stop the run.");
    }
  }, [streamingId, fail]);

  /** Re-ask the most recent user question. */
  const regenerate = useCallback(async () => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    setMessages((prev) => {
      const idx = prev.map((m) => m.role).lastIndexOf("assistant");
      return idx === prev.length - 1 ? prev.slice(0, -1) : prev;
    });
    await sendMessage(lastUser.content);
  }, [messages, sendMessage]);

  const loadConversation = useCallback(
    async (id: string) => {
      const detail = await api.fetchConversationDetail(id);
      setConversationId(detail.id);
      const loaded = detail.messages.map(hydrate);
      setMessages(loaded);

      // A run that was still in flight when the page was closed: re-attach to it
      // rather than leaving the bubble stuck on "Thinking…" forever.
      const live = loaded.find((m) => m.role === "assistant" && (m.status === "pending" || m.status === "running"));
      if (live) {
        setStreamingId(live.id);
        setIsSending(true);
        consumeStream(live.id).finally(() => setIsSending(false));
      }
    },
    [consumeStream]
  );

  const startNewConversation = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setStreamingId(null);
    setConversationId(null);
    setMessages([]);
  }, []);

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      try {
        await api.renameConversation(id, title);
        setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
      } catch (e) {
        fail(e, "Couldn't rename that conversation.");
      }
    },
    [fail]
  );

  const removeConversation = useCallback(
    async (id: string) => {
      try {
        await api.deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (id === conversationId) startNewConversation();
      } catch (e) {
        fail(e, "Couldn't delete that conversation.");
      }
    },
    [conversationId, startNewConversation, fail]
  );

  useEffect(() => () => eventSourceRef.current?.close(), []);

  return {
    conversationId,
    messages,
    isSending,
    streamingId,
    conversations,
    sendMessage,
    stopMessage,
    regenerate,
    loadConversation,
    startNewConversation,
    renameConversation,
    removeConversation,
    refreshConversations,
  };
}
