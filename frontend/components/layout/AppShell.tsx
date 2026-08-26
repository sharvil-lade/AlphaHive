"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { ChatSessionProvider } from "../../contexts/ChatSessionContext";

// Public routes render bare (they scroll, and have their own header/footer). The
// signed-in app renders inside a fixed-height shell with the sidebar.
const PUBLIC_ROUTES = ["/", "/login", "/signup", "/privacy", "/terms"];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (PUBLIC_ROUTES.includes(pathname)) {
    return <div id="main">{children}</div>;
  }

  return (
    <ChatSessionProvider>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main id="main" className="flex-1 flex flex-col overflow-hidden min-w-0">
          {children}
        </main>
      </div>
    </ChatSessionProvider>
  );
}
