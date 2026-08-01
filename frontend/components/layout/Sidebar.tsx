"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageSquare, MessageSquarePlus, Briefcase } from "lucide-react";
import { cn } from "../../lib/utils";
import { useChatSessionContext } from "../../contexts/ChatSessionContext";

// Watchlist, Alerts, and Backtest are parked for a future release — their pages
// still exist in the tree but are no longer linked. The active app is chat +
// (optional) portfolio only.
const NAV_ITEMS = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { conversationId, conversations, loadConversation, startNewConversation } = useChatSessionContext();

  const handleNewChat = () => {
    startNewConversation();
    router.push("/");
  };

  const handleSelectConversation = (id: string) => {
    loadConversation(id);
    router.push(`/chat/${id}`);
  };

  return (
    // Collapsed rail reserves w-16 in normal layout flow; on hover the actual
    // sidebar expands as an overlay (absolute + z-20) so content never reflows.
    <div className="relative w-16 shrink-0 h-full group/sidebar">
      <aside
        className={cn(
          "absolute top-0 left-0 h-full bg-surface border-r border-surface-border flex flex-col",
          "w-16 group-hover/sidebar:w-56 transition-[width] duration-200 ease-out overflow-hidden z-20"
        )}
      >
        <div className="h-14 shrink-0 flex items-center gap-2 px-5 border-b border-surface-border">
          {/* eslint-disable-next-line @next/next/no-img-element -- plain <img> keeps the brand PNG un-optimized/crisp */}
          <img src="/logo.png" alt="Alpha Hive" width={24} height={24} className="w-6 h-6 shrink-0 rounded-md" />
          <span className="text-sm font-semibold tracking-tight whitespace-nowrap opacity-0 group-hover/sidebar:opacity-100 transition-opacity duration-150">
            AlphaHive
          </span>
        </div>

        <nav className="shrink-0 px-2 pt-3 pb-1 space-y-0.5">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors text-mutedText hover:text-foreground hover:bg-surface-hover"
          >
            <MessageSquarePlus className="w-4 h-4 shrink-0" strokeWidth={1.75} />
            <span className="whitespace-nowrap opacity-0 group-hover/sidebar:opacity-100 transition-opacity duration-150">
              New chat
            </span>
          </button>

          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" || pathname.startsWith("/chat/") : pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                  active
                    ? "bg-surface-hover text-foreground"
                    : "text-mutedText hover:text-foreground hover:bg-surface-hover"
                )}
              >
                <Icon className="w-4 h-4 shrink-0" strokeWidth={1.75} />
                <span className="whitespace-nowrap opacity-0 group-hover/sidebar:opacity-100 transition-opacity duration-150">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>

        {/* Only rendered once expanded — a collapsed icon-only rail has no meaningful
            way to represent per-conversation rows, so skip the empty hover targets. */}
        <div className="hidden group-hover/sidebar:flex flex-1 min-h-0 flex-col px-2 pt-2">
          <div className="px-3 pb-1 text-[11px] font-medium text-mutedText/70 uppercase tracking-wide whitespace-nowrap">
            Recents
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto space-y-0.5 pb-2">
            {conversations.length === 0 ? (
              <div className="px-3 py-2 text-xs text-mutedText whitespace-nowrap">No conversations yet</div>
            ) : (
              conversations.map((c) => {
                const active =
                  (pathname === "/" || pathname.startsWith("/chat/")) && c.id === conversationId;
                return (
                  <button
                    key={c.id}
                    onClick={() => handleSelectConversation(c.id)}
                    title={c.title || "New conversation"}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-md text-sm truncate transition-colors",
                      active
                        ? "bg-surface-hover text-foreground"
                        : "text-mutedText hover:text-foreground hover:bg-surface-hover"
                    )}
                  >
                    {c.title || "New conversation"}
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="shrink-0 px-2 py-3">
          <div className="px-3 py-1 text-[11px] text-mutedText text-center whitespace-nowrap opacity-0 group-hover/sidebar:opacity-100 transition-opacity duration-150">
            AlphaHive v1.0
          </div>
        </div>
      </aside>
    </div>
  );
}
