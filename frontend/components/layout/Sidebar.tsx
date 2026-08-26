"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Briefcase,
  Check,
  LogIn,
  Menu,
  MessageSquare,
  MessageSquarePlus,
  Pencil,
  Trash2,
  User as UserIcon,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useChatSessionContext } from "../../contexts/ChatSessionContext";
import { useAuth } from "../../contexts/AuthContext";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { session } = useAuth();
  const {
    conversationId,
    conversations,
    loadConversation,
    startNewConversation,
    renameConversation,
    removeConversation,
  } = useChatSessionContext();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const close = () => setMobileOpen(false);

  const handleNewChat = () => {
    startNewConversation();
    router.push("/chat");
    close();
  };

  const handleSelect = (id: string) => {
    loadConversation(id).catch(() => router.push("/chat"));
    router.push(`/chat/${id}`);
    close();
  };

  const commitRename = async (id: string) => {
    const title = draftTitle.trim();
    setEditingId(null);
    if (title) await renameConversation(id, title);
  };

  const content = (
    <>
      <div className="h-14 shrink-0 flex items-center gap-2 px-5 border-b border-surface-border">
        {/* eslint-disable-next-line @next/next/no-img-element -- plain <img> keeps the brand PNG un-optimized/crisp */}
        <img src="/logo.png" alt="" width={24} height={24} className="w-6 h-6 shrink-0 rounded-md" />
        <span className="text-sm font-semibold tracking-tight whitespace-nowrap sidebar-label">
          Alpha Hive
        </span>
      </div>

      <nav className="shrink-0 px-2 pt-3 pb-1 space-y-0.5" aria-label="Main">
        <button
          onClick={handleNewChat}
          title="New chat"
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors text-mutedText hover:text-foreground hover:bg-surface-hover"
        >
          <MessageSquarePlus className="w-4 h-4 shrink-0" strokeWidth={1.75} />
          <span className="whitespace-nowrap sidebar-label">New chat</span>
        </button>

        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/chat" ? pathname.startsWith("/chat") : pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={close}
              title={item.label}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-surface-hover text-foreground"
                  : "text-mutedText hover:text-foreground hover:bg-surface-hover"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" strokeWidth={1.75} />
              <span className="whitespace-nowrap sidebar-label">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-recents flex-1 min-h-0 flex-col px-2 pt-2">
        <h2 className="px-3 pb-1 text-[11px] font-medium text-mutedText/70 uppercase tracking-wide whitespace-nowrap">
          Recents
        </h2>
        <div className="flex-1 min-h-0 overflow-y-auto space-y-0.5 pb-2">
          {conversations.length === 0 ? (
            <p className="px-3 py-2 text-xs text-mutedText whitespace-nowrap">No conversations yet</p>
          ) : (
            conversations.map((c) => {
              const active = pathname.startsWith("/chat") && c.id === conversationId;

              if (editingId === c.id) {
                return (
                  <div key={c.id} className="flex items-center gap-1 px-2 py-1">
                    <input
                      autoFocus
                      value={draftTitle}
                      onChange={(e) => setDraftTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRename(c.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      aria-label="Conversation title"
                      className="flex-1 min-w-0 bg-surface-raised border border-surface-border rounded px-2 py-1 text-sm"
                    />
                    <button onClick={() => commitRename(c.id)} aria-label="Save title" className="p-1 text-mutedText hover:text-foreground">
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              }

              return (
                <div key={c.id} className="group/row relative flex items-center">
                  <button
                    onClick={() => handleSelect(c.id)}
                    title={c.title || "New conversation"}
                    className={cn(
                      "flex-1 min-w-0 text-left pl-3 pr-14 py-2 rounded-md text-sm truncate transition-colors",
                      active
                        ? "bg-surface-hover text-foreground"
                        : "text-mutedText hover:text-foreground hover:bg-surface-hover"
                    )}
                  >
                    {c.title || "New conversation"}
                  </button>
                  <div className="absolute right-1 flex opacity-0 group-hover/row:opacity-100 focus-within:opacity-100">
                    <button
                      onClick={() => {
                        setEditingId(c.id);
                        setDraftTitle(c.title || "");
                      }}
                      aria-label={`Rename ${c.title || "conversation"}`}
                      className="p-1.5 text-mutedText hover:text-foreground"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => removeConversation(c.id)}
                      aria-label={`Delete ${c.title || "conversation"}`}
                      className="p-1.5 text-mutedText hover:text-bearish"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="shrink-0 px-2 py-3 border-t border-surface-border">
        {session?.authenticated ? (
          <Link
            href="/account"
            onClick={close}
            title="Account"
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
          >
            <UserIcon className="w-4 h-4 shrink-0" strokeWidth={1.75} />
            <span className="truncate sidebar-label">{session.email}</span>
          </Link>
        ) : (
          <Link
            href="/login"
            onClick={close}
            title="Sign in"
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-mutedText hover:text-foreground hover:bg-surface-hover transition-colors"
          >
            <LogIn className="w-4 h-4 shrink-0" strokeWidth={1.75} />
            <span className="whitespace-nowrap sidebar-label">Sign in to save</span>
          </Link>
        )}
      </div>
    </>
  );

  return (
    <>
      {/* Mobile trigger. The desktop rail expands on hover, which touch devices don't
          have — without this the nav was unreachable on a phone entirely. */}
      <button
        onClick={() => setMobileOpen(true)}
        aria-label="Open menu"
        aria-expanded={mobileOpen}
        className="md:hidden fixed top-2.5 left-3 z-30 w-9 h-9 rounded-md flex items-center justify-center text-mutedText hover:text-foreground hover:bg-surface-hover"
      >
        <Menu className="w-5 h-5" />
      </button>

      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50 animate-fade-in"
          onClick={close}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "sidebar bg-surface border-r border-surface-border flex flex-col",
          "fixed inset-y-0 left-0 z-50 w-64 transition-transform duration-200 ease-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          // Desktop: a w-16 rail in normal flow that expands over the content on
          // hover or keyboard focus, so the page never reflows.
          "md:static md:translate-x-0 md:w-16 md:hover:w-56 md:focus-within:w-56",
          "md:transition-[width] md:overflow-hidden md:shrink-0"
        )}
      >
        <button
          onClick={close}
          aria-label="Close menu"
          className="md:hidden absolute top-3 right-3 p-1 text-mutedText hover:text-foreground"
        >
          <X className="w-4 h-4" />
        </button>
        {content}
      </aside>
    </>
  );
}
