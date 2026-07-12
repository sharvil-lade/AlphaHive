"use client";

import { useEffect, useState } from "react";

/** Plain-string client session id, persisted in localStorage — the same
 * session_id convention used across every feature in this app (no auth). */
export function useSessionId(): string {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    let sid = localStorage.getItem("session_id");
    if (!sid) {
      sid = "session_" + Math.random().toString(36).substring(2, 15);
      localStorage.setItem("session_id", sid);
    }
    setSessionId(sid);
  }, []);

  return sessionId;
}
