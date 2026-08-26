# Alpha Hive — Release Checklist

Run through this before exposing Alpha Hive publicly.

## 1. Environment & secrets

- [ ] `.env` filled from `.env.example` (never commit it — it is gitignored).
- [ ] `ENVIRONMENT=production`. The app **refuses to start** if `SECRET_KEY` is weak
      or `CORS_ORIGINS` is `*`, so a misconfigured deploy fails loudly.
- [ ] `SECRET_KEY` is a fresh 48-byte random value, unique to this environment.
      Rotating it signs every user out.
- [ ] `CORS_ORIGINS` lists your exact frontend origin(s), comma-separated.
- [ ] `LITELLM_BASE_URL` / `LITELLM_API_KEY` set — **required for real analysis**.
      Without them the app runs but degrades to a "no LLM configured" fallback.
- [ ] Models resolve on your proxy: `LLM_MODEL_PRIMARY` (specialists),
      `LLM_MODEL_SYNTHESIS` (final decision), `LLM_MODEL_FALLBACK`.
- [ ] Market-data keys present: `FINNHUB_API_KEY`, `TWELVE_DATA_API_KEY`,
      `MARKETAUX_API_KEY` (Indian news).

## 2. Security

- [ ] `COOKIE_SECURE` is on (forced in production) and the site is HTTPS-only —
      the session cookie is the credential.
- [ ] `TRUST_PROXY_HEADERS=true` only if a proxy you control sets
      `X-Forwarded-For`. If the app is internet-facing directly, set it to
      `false` or clients can forge their own rate-limit buckets.
- [ ] Rate limits appropriate for your traffic (`app/main.py`, `limit_*`).
- [ ] Disclaimer visible in chat (`ChatInput`) and enforced in the synthesis
      system prompt ("research, not SEBI-registered advice"). Keep it.
- [ ] `/docs`, `/redoc` and `/openapi.json` are disabled in production (automatic).

## 3. Infrastructure

- [ ] Managed **Postgres** (Supabase), **Redis** and **Qdrant**. Do not run
      production on Docker Desktop over a OneDrive-synced path — observed to drop
      containers mid-run.
- [ ] Serverless/Vercel: use the Supabase **transaction pooler** (port 6543).
      `app/db/session.py` detects it and disables prepared statements and pooling.
- [ ] Migrations applied: `python -m alembic -c alembic.ini upgrade head`.
- [ ] `GET /api/v1/health` returns all three services connected.
      Point load-balancer probes at `/api/v1/health/live` instead — the deep check
      opens three connections per call.
- [ ] Redis retention covers `chat_events:*` (24h TTL) so reconnecting SSE clients
      resume correctly.

## 4. Feature-specific config

- [ ] **SEC filing RAG**: real embeddings only run if `EMBEDDING_MODEL` is set to a
      model your key can reach. If unset, SEC search falls back to a deterministic
      lexical mock — degraded quality, no errors.
- [ ] **PDF reports** (legacy `/agents/run`): `xhtml2pdf` can be blocked by Windows
      Application Control. The import is lazy so it cannot crash startup, but prefer
      a Linux container.

## 5. Smoke tests (against the deployed stack)

- [ ] Sign up, sign out, sign back in. Session survives a browser restart.
- [ ] Add a holding while signed out, then sign up — the holding carries over.
- [ ] Open a second browser profile; confirm it cannot see the first one's
      conversations or portfolio.
- [ ] `POST /chat/conversations` → `.../messages` with "Should I buy Reliance right
      now?" → SSE shows `supervisor` → specialists → `synthesis` → `done`.
- [ ] Answer contains a Bull-vs-Bear section and the compliance disclaimer.
- [ ] Import a portfolio, ask "Analyze my portfolio" → `portfolio_doctor` runs and
      the answer references your actual holdings.
- [ ] "What is a P/E ratio?" → no specialists run (general answer only).
- [ ] Press **Stop** mid-answer → the run halts and partial text is kept.
- [ ] Reload mid-answer → the stream re-attaches instead of hanging.
- [ ] Account → **Export my data** returns JSON; **Delete account** erases it.
- [ ] Open the app on a phone — the menu button opens the sidebar.

## Known limitations (ship-aware)

- **Background runs are in-process.** Agent runs use `asyncio.create_task`, so they
  die if the process restarts, and **will not work on serverless** (Vercel freezes
  the function once the response is returned). Long-running host or a real queue.
- **Rate limiting is per-IP** and fails open when Redis is down. Distributed
  credential stuffing is not covered — add per-account lockout or CAPTCHA if it
  becomes a problem.
- **Comparison mode**: multi-ticker questions deep-analyze the primary ticker only.
- **No billing or usage metering per account.** `MAX_TOKENS_PER_SESSION` is the only
  cost ceiling.
- **No error tracking or LLM tracing** wired up (Sentry, Langfuse).
- **Parked features** (watchlist, alerts, backtest): backend modules retained but not
  mounted in `app/main.py`. Re-enable the routers and rebuild the frontend pages
  together — shipping one half leaves dead routes.
