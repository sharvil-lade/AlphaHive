# 🐝 AlphaHive v1.0

A chat-first AI stock market research assistant built on a **master–slave (supervisor/worker)
agent architecture**. Ask a free-form question about any Indian (NSE/BSE) or global stock — a
**master supervisor agent** plans the work (grounded in your portfolio, if you added one), then
dispatches independent **specialist slave agents** (fundamentals / technical / news-sentiment /
risk). Each specialist is a real LangGraph `create_react_agent` bound to its own **API tools**: it
decides which tools to call, reasons over the results, and reports a verdict. The master then weighs
those verdicts against each other and streams back a clear, conversational decision.

You can optionally **import your Groww portfolio** (via Groww's official Trade API token, or by
uploading a Holdings/P&L export) so the agents research *in the context of what you actually own* —
but the portfolio is entirely optional; the app works as a normal research chat without it.

> **Adding a new capability is a one-liner:** write a `@tool` wrapping an API in
> [`app/agents/tools/`](backend/app/agents/tools/) and add it to a specialist's tool list in
> [`app/agents/specialists.py`](backend/app/agents/specialists.py). The react agent discovers it
> automatically.
>
> _Watchlist, price/RSI/sentiment alerts, and strategy backtesting are parked for a future release —
> the code remains in the tree but is unmounted so the active app is just **chat + portfolio**._

---

## ✨ Features

| Feature | Description |
|---|---|
| **Chat-first research** | Ask anything about a stock in plain language; get a streamed, conversational answer — not a rigid template |
| **Master–slave agent architecture** | A master supervisor agent plans the work and dispatches only the specialist slave agents it needs; each specialist is a real tool-calling `create_react_agent` that fetches its own data, reasons, and reports a verdict; the master then weighs all verdicts (noting where they agree or disagree) into a final decision |
| **APIs as agent tools** | Every data source (quote, profile, technical, news-sentiment, risk, SEC filings, portfolio) is a LangChain `@tool` bound to the agent that needs it — extend the system by adding a tool and assigning it to an agent, no orchestration rewrite |
| **Portfolio-aware research** | Optionally import your Groww holdings; the agents then research any question in the context of what you actually own (concentration, overlap, position sizing) |
| **Groww portfolio import** | Sync holdings via Groww's official Trade API (paste a daily access token), or upload a Holdings/P&L export (CSV/Excel) — no subscription needed for the file path. Fully optional |
| **Live agent trace + chat history** | Watch each agent's status live as it runs; every conversation gets its own URL (`/chat/{id}`) and is listed under "Recents" in the sidebar, ChatGPT-style |
| **India-primary market data** | Yahoo Finance (`.NS`/`.BO`) → BSE India for Indian tickers; Finnhub → Twelve Data → Yahoo Finance for US/global tickers |
| **Real financial news** | Marketaux (finance-specific, real Indian + global coverage) with Finnhub as a US supplement |
| **Any-model LLM routing** | Runs through a LiteLLM proxy — swap models per role (fast model for agents, stronger model for the final synthesis) via env vars, no code changes |
| **Rich response rendering** | Markdown tables, code blocks, and LaTeX formulas (`$$...$$` / `$...$`) render properly — not as raw text |
| **Technical analysis** | RSI, MACD, Bollinger Bands, EMA/SMA crossovers with bullish/bearish scoring |
| **Risk analysis** | Beta (vs Nifty 50 for Indian tickers, S&P 500 otherwise) and annualized volatility |
| **SEC filing RAG** | Download 10-K/10-Q filings, chunk & embed into Qdrant, query with cited answers *(currently limited to a small ticker set — see [docs/PRD.md](docs/PRD.md))* |
| **Investment memo generation** | Institutional-grade PDF & Markdown research reports via the original per-ticker `/agents/run` flow |
| **Portfolio** | Holdings ledger with gain/loss & risk gauges, Groww import, and per-holding beta/volatility — feeds the agents' portfolio context |
| **Parked (future release)** | Watchlist, rules-based alerts (RSI/sentiment/price), and strategy backtesting — code is retained but unmounted |
| **Light / dark mode** | Full theme system (not just a class toggle) — switch from any page header, persists across reloads |
| **Collapsible navigation** | Sidebar collapses to an icon rail and expands on hover, so it never eats into the chat/content area |
| **Observability** | Prometheus metrics at `/metrics`, structured JSON logs, optional Grafana dashboards |

---

## 🛠 Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — async REST API & SSE streaming
- [LangGraph](https://github.com/langchain-ai/langgraph) — multi-agent orchestration (two graphs: a free-form chat graph and the original per-ticker analysis graph)
- LiteLLM-compatible proxy (via the `openai` async client) — provider-agnostic LLM access, one client for every agent
- [SQLAlchemy](https://www.sqlalchemy.org/) (async) + [Alembic](https://alembic.sqlalchemy.org/) — ORM & migrations
- [Qdrant](https://qdrant.tech/) — vector database for SEC RAG
- [Redis](https://redis.io/) — caching, rate limiting, SSE event streaming
- [PostgreSQL](https://www.postgresql.org/) — relational data store (conversations, messages, agent traces, portfolio, watchlist, alerts, reports)

**Frontend**
- [Next.js 15](https://nextjs.org/) (App Router) + React 19
- Tailwind CSS, hand-built on a Vercel Geist-inspired neutral design system (clean, minimal, dark)
- [react-markdown](https://github.com/remarkjs/react-markdown) + `remark-gfm` (tables/code) + `remark-math`/`rehype-katex` (LaTeX)
- [TanStack Query](https://tanstack.com/query) — server-state caching for portfolio/watchlist/alerts/backtest
- Native `EventSource` — live agent-status + streamed-token consumption from the chat SSE endpoint
- [Recharts](https://recharts.org/) — backtest equity curve charting

**Infrastructure**
- [Docker](https://www.docker.com/) + Docker Compose — containerised services
- [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/) — observability (optional)

---

## 📋 Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop/) (for Postgres, Redis, Qdrant)
- A **LiteLLM-compatible proxy** base URL + API key (gives access to whichever models you configure — Claude, Gemini, GPT, etc. all work as long as your proxy routes them)
- Market data API keys (all free-tier):
  - **Finnhub** — [finnhub.io](https://finnhub.io/) (quotes/news, US-focused)
  - **Twelve Data** — [twelvedata.com](https://twelvedata.com/) (quotes/fundamentals fallback)
  - **Marketaux** — [marketaux.com](https://www.marketaux.com/) (news, real Indian + global coverage) — *recommended, without it Indian-ticker news is skipped rather than showing wrong-company results*
  - **Alpha Vantage** (optional, very limited free tier) — [alphavantage.co](https://www.alphavantage.co/)

---

## 🚀 Quick Start (Local Development)

Clone the repo first:

```bash
cd "Groww AI"
```

Everything below is grouped into three independent pieces — **services**, **backend**,
**frontend** — each run from its own terminal, in that order.

### 1. Services (Docker)

Postgres, Redis, and Qdrant — from the **project root**:

```bash
docker compose up -d postgres redis qdrant
docker compose ps
# All three should show status: healthy
```

### 2. Backend

Everything below runs **from inside `backend/`**. Internal imports are relative
(`app.*`), so no `PYTHONPATH` is needed anywhere in this section.

```bash
cd backend
```

**Set up the environment** (one-time):

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# then, either OS:
pip install -r requirements.txt
```

**Configure secrets** — open `.env` in the project root and fill in your keys:

```env
# Database — defaults work with the Docker services above
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234
POSTGRES_DB=AlphaHive
POSTGRES_HOST=localhost
POSTGRES_PORT=5435

REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333

# LLM — LiteLLM proxy. One primary model + one fallback for every agent,
# and a stronger model reserved for the final synthesis/decision step.
LITELLM_BASE_URL=https://your-litellm-proxy/v1
LITELLM_API_KEY=sk-...
LLM_MODEL_PRIMARY=google/gemini-3.5-flash
LLM_MODEL_FALLBACK=anthropic/claude-haiku-4-5
LLM_MODEL_SYNTHESIS=anthropic/claude-sonnet-4-6

# Market data
FINNHUB_API_KEY=your-finnhub-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key   # optional
TWELVE_DATA_API_KEY=your-twelve-data-key
MARKETAUX_API_KEY=your-marketaux-key           # optional but recommended
```

**Run migrations and start the API** (venv already active from setup, so no path prefix needed):

```bash
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now running at **http://localhost:8000** — interactive docs at **http://localhost:8000/docs**

### 3. Frontend

From the **project root**, in a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The app is now running at **http://localhost:3000** 🎉 — ask it something like *"Should I buy Reliance right now?"*

---

## 🐳 Docker Deployment (Full Stack)

```bash
# Build and start all services
docker compose up -d

# Run migrations inside the backend container
docker compose exec backend python -m alembic -c alembic.ini upgrade head

# Check all services are healthy
docker compose ps
```

| Service | URL |
|---|---|
| App | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Prometheus (optional) | http://localhost:9090 |
| Grafana (optional) | http://localhost:3001 |

### With Monitoring (Prometheus + Grafana)

```bash
docker compose --profile monitoring up -d
```

---

## 🧪 Running Tests

```bash
cd backend

# Windows
.venv\Scripts\python.exe -m pytest tests -v

# macOS / Linux
.venv/bin/pytest tests -v
```

Expected output: **23 tests passing** ✅ (requires Postgres + Redis running per Step 1)

---

## 📁 Project Structure

```
Groww AI/
├── backend/
│   ├── .venv/                     # Backend-scoped virtualenv
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py          # Two graphs: create_chat_graph() (master-slave) + create_agent_graph() (legacy per-ticker)
│   │   │   ├── llm.py            # ChatOpenAI (LiteLLM) factory for tool-calling agents
│   │   │   ├── specialists.py    # Agent definitions: master_supervisor + 4 specialist create_react_agents
│   │   │   ├── chat_nodes.py     # Master-slave chat-graph nodes (supervisor + specialist wrappers) + SSE events
│   │   │   ├── state.py          # Shared AgentState (adds tickers/selected_agents/portfolio_context/findings)
│   │   │   ├── utils.py          # Redis-backed log_agent_activity / emit_chat_event
│   │   │   ├── tools/            # APIs as LangChain @tools, grouped per specialist (the extension point)
│   │   │   │   ├── market_tools.py     # get_stock_quote, get_company_profile
│   │   │   │   ├── technical_tools.py  # get_technical_analysis
│   │   │   │   ├── sentiment_tools.py  # get_news_sentiment
│   │   │   │   ├── risk_tools.py       # get_risk_metrics, search_sec_filings
│   │   │   │   └── portfolio_tools.py  # get_user_portfolio (master context)
│   │   │   ├── verdict.py        # Legacy helper used by the per-ticker graph nodes
│   │   │   └── nodes/            # Legacy per-ticker (create_agent_graph) nodes + chat synthesis node
│   │   │       ├── research.py     # (legacy) Fundamentals node
│   │   │       ├── technical.py    # (legacy) Technical node
│   │   │       ├── news.py         # (legacy) News/sentiment node
│   │   │       ├── risk.py         # (legacy) Risk node (Nifty 50 / S&P 500 beta)
│   │   │       ├── synthesis.py    # Chat graph exit: weighs specialist verdicts + portfolio, streams the answer
│   │   │       └── decision.py     # Per-ticker graph exit: full memo + PDF/DB report
│   │   ├── api/v1/endpoints/     # chat, stocks, indicators, sentiment, sec, agents, reports,
│   │   │                         # portfolio, watchlist, alerts, backtest
│   │   ├── core/                 # Config, logging, rate limiter, metrics
│   │   ├── models/                # SQLAlchemy models (incl. Conversation/Message/AgentTrace)
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── llm_client.py       # Single LiteLLM-backed client every agent calls through
│   │   │   ├── chat_service.py     # Conversation/Message/AgentTrace persistence
│   │   │   ├── stock_service.py    # India-primary quote/profile/history sourcing
│   │   │   ├── news_service.py     # Marketaux-primary news sourcing
│   │   │   └── sentiment_service.py
│   │   └── main.py
│   ├── alembic/versions/         # Migrations (initial schema + chat models)
│   └── tests/                    # pytest suite (23 tests)
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Chat home ("/", new conversation)
│   │   ├── chat/[conversationId]/ # A specific conversation's URL (ChatGPT-style)
│   │   ├── portfolio/, watchlist/, alerts/, backtest/   # Secondary routes
│   │   ├── icon.svg                # App favicon (Next.js auto-detects this file)
│   │   ├── theme-provider.tsx      # next-themes wrapper (light/dark mode)
│   │   └── layout.tsx, providers.tsx, globals.css
│   ├── components/
│   │   ├── chat/                 # ChatView, MessageBubble, AgentTracePanel, ChatInput
│   │   ├── layout/                # Sidebar (hover-to-expand nav + Recents), ThemeToggle
│   │   └── ui/primitives.tsx
│   ├── contexts/ChatSessionContext.tsx   # Shared chat session state (Sidebar + ChatView both read it)
│   ├── hooks/useChatSession.ts   # Streaming chat state (POST message -> EventSource -> live state)
│   └── services/api.ts           # Typed fetch client for every backend endpoint
├── docs/                         # PRD.md, ADD.md, Implementation_Plan.md, DEPLOYMENT.md
├── ANALYSIS.md                   # Architecture snapshot, market research, roadmap
├── docker-compose.yml
├── Makefile
└── .env
```

---

## ⚙️ Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat/conversations` | Create a chat conversation |
| `GET` | `/api/v1/chat/conversations?session_id=` | List a session's conversations |
| `GET` | `/api/v1/chat/conversations/{id}` | Full message history + agent traces |
| `POST` | `/api/v1/chat/conversations/{id}/messages` | Post a free-form query; kicks off the agent graph in the background |
| `GET` | `/api/v1/chat/messages/{id}/stream` | SSE stream of live agent-status + streamed answer text |
| `GET` | `/api/v1/stocks/quote?symbol=` | Real-time price quote |
| `GET` | `/api/v1/indicators/ta?symbol=` | Technical analysis score |
| `GET` | `/api/v1/sentiment/summary?symbol=` | News sentiment summary |
| `POST` | `/api/v1/sec/{symbol}/index` | Index SEC filings into Qdrant |
| `GET` | `/api/v1/portfolios/summary?session_id=` | Portfolio value, gain/loss, and per-holding risk |
| `POST` | `/api/v1/portfolios/import/groww?session_id=` | Import holdings via a Groww Trade API access token |
| `POST` | `/api/v1/portfolios/import/file?session_id=` | Import holdings from an uploaded Groww CSV/Excel export |
| `POST` | `/api/v1/agents/run` | Launch the original per-ticker deep-dive workflow (legacy memo flow) |
| `GET` | `/api/v1/reports/{id}/download/pdf` | Download PDF investment memo |
| `GET` | `/api/v1/health` | Deep health check (Postgres + Redis + Qdrant) |
| `GET` | `/metrics` | Prometheus metrics |

Full interactive documentation: **http://localhost:8000/docs**

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LITELLM_BASE_URL` | ✅ | — | Your LiteLLM-compatible proxy URL |
| `LITELLM_API_KEY` | ✅ | — | Proxy API key |
| `LLM_MODEL_PRIMARY` | ❌ | `google/gemini-3.5-flash` | Fast model for the router + specialist agents |
| `LLM_MODEL_FALLBACK` | ❌ | `anthropic/claude-haiku-4-5` | Used if the primary model errors/times out |
| `LLM_MODEL_SYNTHESIS` | ❌ | `anthropic/claude-sonnet-4-6` | Stronger model for the final synthesized answer |
| `FINNHUB_API_KEY` | ✅ | — | US quotes & news |
| `TWELVE_DATA_API_KEY` | ✅ | — | Quote/fundamentals fallback |
| `MARKETAUX_API_KEY` | ❌ | — | Real financial news, incl. Indian coverage |
| `ALPHA_VANTAGE_API_KEY` | ❌ | — | Historical data fallback |
| `POSTGRES_PASSWORD` | ✅ | `postgrespassword` | Change in production |
| `ENVIRONMENT` | ❌ | `development` | Set to `production` for JSON logs |
| `MAX_TOKENS_PER_SESSION` | ❌ | `100000` | LLM token budget cap per session |
| `CORS_ORIGINS` | ❌ | `*` | Restrict to your domain in production |

---

## 📖 More Documentation

- [Analysis & Roadmap](ANALYSIS.md) — architecture snapshot, market research, and suggested next features
- [Full Deployment Guide](docs/DEPLOYMENT.md) — production setup, security checklist, Grafana, troubleshooting
- [Product Requirements](docs/PRD.md) / [Architecture](docs/ADD.md) — background and design decisions
- [API Interactive Docs](http://localhost:8000/docs) — try every endpoint in the browser
