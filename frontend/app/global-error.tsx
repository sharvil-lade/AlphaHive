"use client";

// Catches errors thrown in the root layout itself, where `app/error.tsx` cannot
// render. It must supply its own <html>/<body>.
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", padding: "4rem 1.5rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Alpha Hive failed to load</h1>
        <p style={{ marginTop: "0.5rem", color: "#71717a" }}>Please refresh the page.</p>
        {error.digest && <p style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#71717a" }}>Ref: {error.digest}</p>}
        <button onClick={reset} style={{ marginTop: "1.5rem", padding: "0.5rem 1rem", cursor: "pointer" }}>
          Try again
        </button>
      </body>
    </html>
  );
}
