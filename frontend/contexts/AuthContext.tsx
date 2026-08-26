"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import * as api from "../services/api";
import type { Session } from "../services/api";

interface AuthContextValue {
  session: Session | null;
  /** True until the first /auth/session call settles. */
  loading: boolean;
  signup: (email: string, password: string, name?: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  // Also mints the anonymous session cookie on a first visit, which every other
  // request depends on — so it runs once, before anything else talks to the API.
  const refresh = useCallback(async () => {
    try {
      setSession(await api.fetchSession());
    } catch {
      setSession({ authenticated: false });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signup = useCallback(async (email: string, password: string, name?: string) => {
    setSession(await api.signup(email, password, name));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setSession(await api.login(email, password));
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    // Full reload rather than a state reset: it clears every cached query and any
    // in-memory chat history belonging to the account that just signed out.
    window.location.href = "/";
  }, []);

  return (
    <AuthContext.Provider value={{ session, loading, signup, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
