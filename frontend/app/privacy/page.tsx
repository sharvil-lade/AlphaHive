import type { Metadata } from "next";
import { MarketingShell } from "../../components/marketing/MarketingShell";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "What Alpha Hive collects, why, how long it is kept, and how to delete it.",
};

const UPDATED = "25 August 2026";

export default function PrivacyPage() {
  return (
    <MarketingShell>
      <article className="max-w-2xl mx-auto px-6 py-16 chat-prose">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Privacy Policy</h1>
        <p className="text-[13px] text-mutedText mb-8">Last updated: {UPDATED}</p>

        <h2>What we collect</h2>
        <ul>
          <li>
            <strong>Account details</strong> — your email address, an optional display name, and a
            hashed password. We never store your password in readable form.
          </li>
          <li>
            <strong>Your research</strong> — the questions you ask and the answers the agents
            produce, so your history is there when you come back.
          </li>
          <li>
            <strong>Portfolio holdings</strong> — only if you choose to add or import them. This is
            optional and Alpha Hive works fully without it.
          </li>
          <li>
            <strong>A session cookie</strong> — a single httpOnly cookie that identifies your
            session. It is strictly necessary for the service to function, so no consent banner is
            required for it. We use no advertising or third-party tracking cookies.
          </li>
        </ul>

        <h2>Your Groww access token</h2>
        <p>
          If you import holdings using a Groww access token, that token is used for the duration of
          that single request and is <strong>never written to our database or logs</strong>. If you
          upload a statement instead, the file is parsed in memory and discarded.
        </p>

        <h2>How we use it</h2>
        <p>
          Only to run the service: to answer your questions, to ground those answers in your
          holdings when you ask portfolio questions, and to keep your history. We do not sell your
          data, and we do not use it to build advertising profiles.
        </p>

        <h2>Third parties</h2>
        <p>
          To answer a question we send the text of that question, and relevant market data, to our
          language-model provider. We also read public market data from providers such as Yahoo
          Finance, Finnhub, Twelve Data and Marketaux. Your email address and password are never
          shared with any of them.
        </p>

        <h2>Retention</h2>
        <p>
          We keep your data until you delete it. Anonymous sessions are tied to a browser cookie; if
          you clear it without creating an account, that data becomes unreachable.
        </p>

        <h2>Your rights</h2>
        <p>
          Under India&apos;s Digital Personal Data Protection Act and the GDPR you can access,
          export and erase your data. Both are self-service: go to{" "}
          <strong>Account</strong> and use <strong>Export my data</strong> or{" "}
          <strong>Delete account</strong>. Deletion is immediate and permanent.
        </p>

        <h2>Security</h2>
        <p>
          Passwords are hashed with bcrypt. Session cookies are httpOnly, SameSite=Lax and
          HTTPS-only in production, so they cannot be read by JavaScript. Data is transmitted over
          TLS.
        </p>

        <h2>Contact</h2>
        <p>
          Questions about this policy, or a data request you cannot complete yourself? Reach us
          through the contact address published on our repository.
        </p>
      </article>
    </MarketingShell>
  );
}
