"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { ApiError } from "../../services/api";
import { Button, Input } from "../ui/primitives";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const isSignup = mode === "signup";
  const { login, signup } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isSignup) await signup(email, password, name);
      else await login(email, password);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-12">
      <Link href="/" className="flex items-center gap-2 mb-8">
        {/* eslint-disable-next-line @next/next/no-img-element -- plain <img> keeps the brand PNG un-optimized/crisp */}
        <img src="/logo.png" alt="" width={28} height={28} className="w-7 h-7 rounded-md" />
        <span className="text-base font-semibold tracking-tight">Alpha Hive</span>
      </Link>

      <div className="w-full max-w-sm">
        <h1 className="text-xl font-semibold tracking-tight mb-1.5">
          {isSignup ? "Create your account" : "Welcome back"}
        </h1>
        <p className="text-sm text-mutedText mb-6">
          {isSignup
            ? "Your current portfolio and chat history carry over."
            : "Sign in to reach your research from any device."}
        </p>

        <form onSubmit={submit} className="space-y-3.5" noValidate>
          {isSignup && (
            <div>
              <label htmlFor="name" className="text-[12px] text-mutedText block mb-1.5">
                Name <span className="opacity-60">(optional)</span>
              </label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                className="w-full"
              />
            </div>
          )}

          <div>
            <label htmlFor="email" className="text-[12px] text-mutedText block mb-1.5">
              Email
            </label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full"
            />
          </div>

          <div>
            <label htmlFor="password" className="text-[12px] text-mutedText block mb-1.5">
              Password
            </label>
            <Input
              id="password"
              type="password"
              required
              minLength={isSignup ? 8 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isSignup ? "new-password" : "current-password"}
              className="w-full"
            />
            {isSignup && <p className="text-[11px] text-mutedText mt-1.5">At least 8 characters.</p>}
          </div>

          {error && (
            <p role="alert" className="text-[13px] text-bearish">
              {error}
            </p>
          )}

          <Button type="submit" disabled={busy} className="w-full !py-2">
            {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {isSignup ? "Create account" : "Sign in"}
          </Button>
        </form>

        <p className="text-[13px] text-mutedText mt-5 text-center">
          {isSignup ? (
            <>
              Already have an account?{" "}
              <Link href="/login" className="text-foreground underline underline-offset-2">
                Sign in
              </Link>
            </>
          ) : (
            <>
              No account?{" "}
              <Link href="/signup" className="text-foreground underline underline-offset-2">
                Create one
              </Link>
            </>
          )}
        </p>

        <p className="text-[13px] text-mutedText mt-2 text-center">
          <Link href="/chat" className="hover:text-foreground transition-colors">
            Continue without an account
          </Link>
        </p>
      </div>
    </div>
  );
}
