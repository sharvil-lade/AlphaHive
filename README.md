# 🏦 AI Hedge Fund Analyst Platform

A production-grade, full-stack AI investment research platform that combines real-time market data, multi-agent LLM orchestration, SEC filing analysis, and automated portfolio management into a single unified dashboard.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Real-time Market Data** | Live quotes, historical OHLCV charts, and company profiles via Finnhub & yFinance |
| **Technical Analysis** | RSI, MACD, Bollinger Bands, EMA/SMA crossovers with bullish/bearish scoring |
| **Sentiment Analysis** | News-driven NLP scoring with opportunity/threat extraction |
| **SEC Filing RAG** | Download 10-K/10-Q filings, chunk & embed into Qdrant, query with cited answers |
| **Multi-Agent AI System** | LangGraph state machine with 5 specialized agents (Market, Technical, Sentiment, SEC, Decision) |
| **Investment Memo Generation** | Institutional-grade PDF & Markdown research reports with buy/hold/sell recommendations |
| **Portfolio Management** | Holdings ledger, sector weight visualiser, gain/loss tracker, and risk gauges |
| **Watchlist & Alerts** | Symbol watchlists + rules-based alerts (RSI, sentiment, price threshold) |
| **Backtesting Engine** | Simulate RSI, EMA crossover, and MACD strategies vs S&P 500 benchmark |
| **Observability** | Prometheus metrics at `/metrics`, structured JSON logs, optional Grafana dashboards |

---

## 🛠 Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — async REST API & SSE streaming
- [LangGraph](https://github.com/langchain-ai/langgraph) + [LangChain](https://python.langchain.com/) — multi-agent orchestration
- [SQLAlchemy](https://www.sqlalchemy.org/) (async) + [Alembic](https://alembic.sqlalchemy.org/) — ORM & migrations
- [Qdrant](https://qdrant.tech/) — vector database for SEC RAG
- [Redis](https://redis.io/) — caching, rate limiting, SSE log buffer
- [PostgreSQL](https://www.postgresql.org/) — relational data store

**Frontend**
- [Next.js 14](https://nextjs.org/) — React framework
- [Recharts](https://recharts.org/) — financial charting
- [Tailwind CSS](https://tailwindcss.com/) — styling

**Infrastructure**
- [Docker](https://www.docker.com/) + Docker Compose — containerised services
- [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/) — observability (optional)

---

## 📋 Prerequisites

Before you start, make sure you have:

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop/) (for Postgres, Redis, Qdrant)
- API keys for:
  - **OpenAI** — [platform.openai.com](https://platform.openai.com/)
  - **Finnhub** — [finnhub.io](https://finnhub.io/) (free tier works)
  - **Alpha Vantage** (optional) — [alphavantage.co](https://www.alphavantage.co/)

---

## 🚀 Quick Start (Local Development)

### Step 1 — Clone and enter the project

```bash
cd "Groww AI"
```

### Step 2 — Create a Python virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install Python dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 4 — Configure environment variables

Open `.env` in the project root and fill in your API keys:

```env
# Financial & AI API Keys
OPENAI_API_KEY=sk-your-key-here
FINNHUB_API_KEY=your-finnhub-key-here
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key-here   # optional

# Everything else is pre-configured for local Docker services
```

### Step 5 — Start the infrastructure containers

```bash
docker compose up -d postgres redis qdrant
```

Wait a few seconds for the containers to become healthy, then verify:

```bash
docker compose ps
# All three should show status: healthy
```

### Step 6 — Run database migrations

```bash
# Windows
$env:PYTHONPATH="C:\path\to\Groww AI"; .venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head

# macOS / Linux
PYTHONPATH=. .venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

### Step 7 — Start the backend API

```bash
# Windows
$env:PYTHONPATH="C:\path\to\Groww AI"; .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# macOS / Linux
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now running at **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

### Step 8 — Start the frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

The dashboard is now running at **http://localhost:3000** 🎉

---

## 🐳 Docker Deployment (Full Stack)

To run everything in containers:

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
| Dashboard | http://localhost:3000 |
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
# Windows
$env:PYTHONPATH="C:\path\to\Groww AI"; .venv\Scripts\python.exe -m pytest backend/tests -v

# macOS / Linux
PYTHONPATH=. .venv/bin/pytest backend/tests -v
```

Expected output: **23 tests passing** ✅

---

## 📁 Project Structure

```
Groww AI/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph multi-agent nodes & graph
│   │   ├── api/v1/          # FastAPI route endpoints
│   │   ├── core/            # Config, logging, rate limiter, metrics
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic services
│   │   ├── templates/       # Jinja2 HTML templates (PDF reports)
│   │   └── main.py          # FastAPI app entry point
│   ├── alembic/             # Database migration scripts
│   ├── scripts/             # Utility scripts (TypeScript type gen)
│   ├── tests/               # pytest test suite (23 tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js app router pages
│   ├── hooks/               # React hooks (useAgentStream SSE)
│   ├── services/            # Typed API client (api.ts)
│   ├── types/               # Generated TypeScript types
│   └── Dockerfile
├── docs/
│   ├── DEPLOYMENT.md        # Full production deployment guide
│   └── PRD.md               # Product requirements document
├── docker-compose.yml       # Full stack orchestration
├── prometheus.yml           # Prometheus scrape config
├── Makefile                 # Developer shortcuts
└── .env                     # Local environment variables
```

---

## ⚙️ Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/stocks/{symbol}/quote` | Real-time price quote |
| `GET` | `/api/v1/indicators/{symbol}/posture` | Technical analysis score |
| `GET` | `/api/v1/sentiment/{symbol}` | News sentiment summary |
| `POST` | `/api/v1/sec/{symbol}/index` | Index SEC filings into Qdrant |
| `POST` | `/api/v1/agents/run` | Launch AI analysis workflow |
| `GET` | `/api/v1/agents/run/{id}/stream` | Stream live agent logs (SSE) |
| `GET` | `/api/v1/reports/{id}/download/pdf` | Download PDF investment memo |
| `POST` | `/api/v1/backtest/run` | Run a backtesting simulation |
| `GET` | `/api/v1/health` | Deep health check (Postgres + Redis + Qdrant) |
| `GET` | `/metrics` | Prometheus metrics |

Full interactive documentation: **http://localhost:8000/docs**

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | Powers all LLM agent nodes |
| `FINNHUB_API_KEY` | ✅ | — | Real-time stock quotes & news |
| `ALPHA_VANTAGE_API_KEY` | ❌ | — | Historical data fallback |
| `POSTGRES_PASSWORD` | ✅ | `postgrespassword` | Change in production |
| `ENVIRONMENT` | ❌ | `development` | Set to `production` for JSON logs |
| `MAX_TOKENS_PER_SESSION` | ❌ | `100000` | LLM token budget cap per session |
| `CORS_ORIGINS` | ❌ | `*` | Restrict to your domain in production |

---

## 📖 More Documentation

- [Full Deployment Guide](docs/DEPLOYMENT.md) — production setup, security checklist, Grafana, troubleshooting
- [API Interactive Docs](http://localhost:8000/docs) — try every endpoint in the browser
