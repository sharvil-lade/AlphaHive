"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "../components/ui/primitives";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Replace with your error tracker (Sentry.captureException) when one is wired up.
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-xl font-semibold tracking-tight">Something went wrong</h1>
      <p className="text-sm text-mutedText max-w-sm">
        That page hit an unexpected error. Trying again usually works.
      </p>
      {error.digest && <p className="text-[11px] font-mono text-mutedText">Ref: {error.digest}</p>}
      <div className="flex gap-2">
        <Button onClick={reset}>Try again</Button>
        <Link href="/chat">
          <Button variant="outline">Back to chat</Button>
        </Link>
      </div>
    </div>
  );
}
