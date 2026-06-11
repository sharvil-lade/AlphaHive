import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from qdrant_client import QdrantClient

from backend.app.core.config import settings
from backend.app.core.logging_config import configure_logging
from backend.app.db.session import get_db

# ── Structured logging must be configured before any module-level loggers fire ──
configure_logging(
    level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
    json_output=(settings.ENVIRONMENT == "production"),
)

import logging
logger = logging.getLogger("hedge-fund-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager handling startup and shutdown actions."""
    logger.info(
        "Initializing AI Hedge Fund Analyst Platform API",
        extra={
            "environment": settings.ENVIRONMENT,
            "postgres": f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}",
            "redis": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            "qdrant": f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
        }
    )
    yield
    logger.info("Shutting down API service")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

from backend.app.api.v1.endpoints.stocks import router as stocks_router
from backend.app.api.v1.endpoints.indicators import router as indicators_router
from backend.app.api.v1.endpoints.sentiment import router as sentiment_router
from backend.app.api.v1.endpoints.sec import router as sec_router
from backend.app.api.v1.endpoints.agents import router as agents_router
from backend.app.api.v1.endpoints.reports import router as reports_router
from backend.app.api.v1.endpoints.portfolio import router as portfolio_router
from backend.app.api.v1.endpoints.watchlist import router as watchlist_router
from backend.app.api.v1.endpoints.alerts import router as alerts_router
from backend.app.api.v1.endpoints.backtest import router as backtest_router
from fastapi.responses import PlainTextResponse
from backend.app.core.rate_limiter import limit_60_per_min, limit_10_per_min
from backend.app.core.metrics import MetricsMiddleware
from backend.app.core import metrics


# ── CORS ── Use configured origins (hardened in production via CORS_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus-style request metrics collection ──
app.add_middleware(MetricsMiddleware)


# ── Register routers with rate-limiting constraints ──
app.include_router(stocks_router,    prefix=f"{settings.API_V1_STR}/stocks",     tags=["stocks"],     dependencies=[Depends(limit_60_per_min)])
app.include_router(indicators_router,prefix=f"{settings.API_V1_STR}/indicators", tags=["indicators"], dependencies=[Depends(limit_60_per_min)])
app.include_router(sentiment_router, prefix=f"{settings.API_V1_STR}/sentiment",  tags=["sentiment"],  dependencies=[Depends(limit_60_per_min)])
app.include_router(sec_router,       prefix=f"{settings.API_V1_STR}/sec",        tags=["sec"],        dependencies=[Depends(limit_60_per_min)])
app.include_router(agents_router,    prefix=f"{settings.API_V1_STR}/agents",     tags=["agents"],     dependencies=[Depends(limit_10_per_min)])
app.include_router(reports_router,   prefix=f"{settings.API_V1_STR}/reports",    tags=["reports"],    dependencies=[Depends(limit_60_per_min)])
app.include_router(portfolio_router, prefix=f"{settings.API_V1_STR}/portfolios", tags=["portfolios"], dependencies=[Depends(limit_60_per_min)])
app.include_router(watchlist_router, prefix=f"{settings.API_V1_STR}/watchlist",  tags=["watchlist"],  dependencies=[Depends(limit_60_per_min)])
app.include_router(alerts_router,    prefix=f"{settings.API_V1_STR}/alerts",     tags=["alerts"],     dependencies=[Depends(limit_60_per_min)])
app.include_router(backtest_router,  prefix=f"{settings.API_V1_STR}/backtest",   tags=["backtest"],   dependencies=[Depends(limit_60_per_min)])


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics_endpoint():
    """Expose Prometheus-formatted API telemetry metrics."""
    if metrics.metrics_collector:
        return metrics.metrics_collector.get_prometheus_metrics()
    return "# Metrics collector not initialized.\n"


@app.get("/", include_in_schema=False)
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }


@app.get(f"{settings.API_V1_STR}/health", tags=["ops"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Deep health check verifying connections to Postgres, Redis, and Qdrant.

    Returns:
        dict: Health status of each individual service component.
    """
    health_results = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "postgres": "unknown",
        "redis": "unknown",
        "qdrant": "unknown",
    }

    # 1. Verify PostgreSQL Connection (Async)
    try:
        start_time = time.time()
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            latency = (time.time() - start_time) * 1000
            health_results["postgres"] = f"connected ({latency:.2f}ms)"
        else:
            health_results["postgres"] = "unhealthy (unexpected output)"
            health_results["status"] = "unhealthy"
    except Exception as e:
        logger.error("PostgreSQL health check failed", extra={"error": str(e)})
        health_results["postgres"] = f"failed: {str(e)}"
        health_results["status"] = "unhealthy"

    # 2. Verify Redis Connection (Async)
    try:
        start_time = time.time()
        redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_timeout=2)
        ping_response = await redis_client.ping()
        await redis_client.aclose()
        if ping_response:
            latency = (time.time() - start_time) * 1000
            health_results["redis"] = f"connected ({latency:.2f}ms)"
        else:
            health_results["redis"] = "unhealthy (ping failed)"
            health_results["status"] = "unhealthy"
    except Exception as e:
        logger.error("Redis health check failed", extra={"error": str(e)})
        health_results["redis"] = f"failed: {str(e)}"
        health_results["status"] = "unhealthy"

    # 3. Verify Qdrant Connection
    try:
        start_time = time.time()
        qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2)
        qdrant_client.get_collections()
        latency = (time.time() - start_time) * 1000
        health_results["qdrant"] = f"connected ({latency:.2f}ms)"
    except Exception as e:
        logger.error("Qdrant health check failed", extra={"error": str(e)})
        health_results["qdrant"] = f"failed: {str(e)}"
        health_results["status"] = "unhealthy"

    if health_results["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=health_results
        )

    return health_results
