"use client";

import { useEffect, useState } from "react";

/** Client session id, persisted in localStorage — the session_id convention used
 * across the app (no accounts yet). It keys the user's private data (portfolio),
 * so it must be unguessable: a 122-bit crypto UUID, not Math.random(), so a
 * portfolio can't be enumerated by trying sequential/short ids. */
function generateSessionId(): string {
  // Client-only hook, so window.crypto is available and unambiguously the DOM Crypto.
  const c = window.crypto;
  const uuid =
    typeof c.randomUUID === "function"
      ? c.randomUUID()
      : // Fallback for older browsers: 16 crypto-random bytes as hex.
        Array.from(c.getRandomValues(new Uint8Array(16)))
          .map((b) => b.toString(16).padStart(2, "0"))
          .join("");
  return `session_${uuid}`;
}

export function useSessionId(): string {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    let sid = localStorage.getItem("session_id");
    // Migrate legacy short/guessable ids to a strong one (old key had no dashes
    // and was < 24 chars); anything already UUID-shaped is kept as-is.
    if (!sid || sid.length < 24) {
      sid = generateSessionId();
      localStorage.setItem("session_id", sid);
    }
    setSessionId(sid);
  }, []);

  return sessionId;
}
