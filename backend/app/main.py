import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.redis import close_redis, get_redis
from app.db.session import get_db

# ── Structured logging must be configured before any module-level loggers fire ──
configure_logging(
    level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
    json_output=settings.is_production(),
)

logger = logging.getLogger("alphahive-backend")


async def _fail_orphaned_runs() -> None:
    """Close out messages left mid-run by a previous process.

    Agent runs are in-process asyncio tasks, so a restart kills them and leaves the
    message `pending` forever — the UI then shows "Thinking…" on every reload with
    nothing behind it. Marking them on boot is what makes a restart self-healing.

    ponytail: assumes one backend process. With multiple replicas this would also
    fail runs that are still live on a sibling — move to a task queue before scaling out.
    """
    from sqlalchemy import update

    from app.db.session import AsyncSessionLocal
    from app.models.models import Message

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(Message)
                .where(Message.role == "assistant", Message.status.in_(("pending", "running")))
                .values(status="failed", content="This run was interrupted. Please ask again.")
            )
            await db.commit()
            if result.rowcount:
                logger.info(f"Closed {result.rowcount} interrupted run(s) from a previous process")
    except Exception as e:
        logger.error(f"Could not reconcile interrupted runs: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager handling startup and shutdown actions."""
    logger.info(
        f"Initializing {settings.PROJECT_NAME} API",
        extra={
            "environment": settings.ENVIRONMENT,
            "postgres": f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}",
            "redis": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        },
    )
    # Hard guardrails (SECRET_KEY, CORS) fail at import time in app.core.config.
    if settings.is_production() and settings.POSTGRES_PASSWORD in (
        "postgrespassword",
        "1234",
        "postgres",
        "",
    ):
        logger.warning("SECURITY: POSTGRES_PASSWORD is a default/weak value in production — change it.")

    await _fail_orphaned_runs()

    yield

    logger.info("Shutting down API service")
    from app.db.session import engine

    await engine.dispose()
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    # Docs are a free map of the attack surface in production.
    docs_url=None if settings.is_production() else "/docs",
    redoc_url=None if settings.is_production() else "/redoc",
    openapi_url=None if settings.is_production() else "/openapi.json",
)

from app.api.v1.endpoints.agents import router as agents_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.indicators import router as indicators_router
from app.api.v1.endpoints.portfolio import router as portfolio_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.sec import router as sec_router
from app.api.v1.endpoints.sentiment import router as sentiment_router
from app.api.v1.endpoints.stocks import router as stocks_router
from app.core import metrics
from app.core.metrics import MetricsMiddleware
from app.core.rate_limiter import limit_10_per_min, limit_60_per_min, limit_auth

# ── CORS ──
# Credentialed, because identity is an httpOnly cookie. A wildcard origin is
# spec-invalid with credentials and is rejected at startup in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# ── Prometheus-style request metrics collection ──
app.add_middleware(MetricsMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Tag requests so a user-facing error can be matched to its log line."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Error handling ──
# Driver errors and connection strings are logged server-side only; the client gets a
# stable message plus the request id.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled error",
        extra={"request_id": request_id, "path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong on our end.", "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Flatten pydantic's error list into one readable sentence for the UI."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query"))
    message = first.get("msg", "Invalid request.")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"{field}: {message}" if field else message},
    )


# ── Register routers with rate-limiting constraints ──
V1 = settings.API_V1_STR
app.include_router(auth_router, prefix=f"{V1}/auth", tags=["auth"], dependencies=[Depends(limit_auth)])
app.include_router(
    stocks_router, prefix=f"{V1}/stocks", tags=["stocks"], dependencies=[Depends(limit_60_per_min)]
)
app.include_router(
    indicators_router,
    prefix=f"{V1}/indicators",
    tags=["indicators"],
    dependencies=[Depends(limit_60_per_min)],
)
app.include_router(
    sentiment_router, prefix=f"{V1}/sentiment", tags=["sentiment"], dependencies=[Depends(limit_60_per_min)]
)
app.include_router(sec_router, prefix=f"{V1}/sec", tags=["sec"], dependencies=[Depends(limit_60_per_min)])
app.include_router(
    agents_router, prefix=f"{V1}/agents", tags=["agents"], dependencies=[Depends(limit_10_per_min)]
)
app.include_router(
    reports_router, prefix=f"{V1}/reports", tags=["reports"], dependencies=[Depends(limit_60_per_min)]
)
app.include_router(
    portfolio_router, prefix=f"{V1}/portfolios", tags=["portfolios"], dependencies=[Depends(limit_60_per_min)]
)
app.include_router(chat_router, prefix=f"{V1}/chat", tags=["chat"], dependencies=[Depends(limit_60_per_min)])


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics_endpoint():
    """Expose Prometheus-formatted API telemetry metrics."""
    if metrics.metrics_collector:
        return metrics.metrics_collector.get_prometheus_metrics()
    return "# Metrics collector not initialized.\n"


@app.get("/", include_in_schema=False)
def read_root():
    return {"status": "online", "service": settings.PROJECT_NAME, "environment": settings.ENVIRONMENT}


@app.get(f"{V1}/health/live", tags=["ops"])
async def liveness():
    """Cheap liveness probe. Separate from the deep check so a load balancer polling
    every few seconds doesn't open three connections each time."""
    return {"status": "alive"}


@app.get(f"{V1}/health", tags=["ops"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Deep readiness check verifying connections to Postgres and Redis."""
    health_results = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "postgres": "unknown",
        "redis": "unknown",
    }

    def _fail(component: str, error: Exception) -> None:
        # Log the real cause; return only that the component is down.
        logger.error(f"{component} health check failed", extra={"error": str(error)})
        health_results[component] = "unavailable"
        health_results["status"] = "unhealthy"

    try:
        start_time = time.time()
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            health_results["postgres"] = f"connected ({(time.time() - start_time) * 1000:.2f}ms)"
        else:
            _fail("postgres", RuntimeError("unexpected SELECT 1 result"))
    except Exception as e:
        _fail("postgres", e)

    try:
        start_time = time.time()
        if await get_redis().ping():
            health_results["redis"] = f"connected ({(time.time() - start_time) * 1000:.2f}ms)"
        else:
            _fail("redis", RuntimeError("ping failed"))
    except Exception as e:
        _fail("redis", e)

    if health_results["status"] == "unhealthy":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_results)

    return health_results
