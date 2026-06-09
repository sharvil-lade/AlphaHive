import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from qdrant_client import QdrantClient

from backend.app.core.config import settings
from backend.app.db.session import get_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("hedge-fund-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager handling startup and shutdown actions."""
    logger.info("Initializing AI Hedge Fund Analyst Platform API...")
    logger.info(f"Connecting to database: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    logger.info(f"Connecting to Redis cache: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"Connecting to Qdrant vector space: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    yield
    logger.info("Shutting down API service...")


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

# Enable CORS for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(stocks_router, prefix=f"{settings.API_V1_STR}/stocks", tags=["stocks"])
app.include_router(indicators_router, prefix=f"{settings.API_V1_STR}/indicators", tags=["indicators"])
app.include_router(sentiment_router, prefix=f"{settings.API_V1_STR}/sentiment", tags=["sentiment"])
app.include_router(sec_router, prefix=f"{settings.API_V1_STR}/sec", tags=["sec"])


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs"
    }


@app.get(f"{settings.API_V1_STR}/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Deep health check verifying connections to Postgres, Redis, and Qdrant.

    Returns:
        dict: Health status of each individual service component.
    """
    health_results = {
        "status": "healthy",
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
        logger.error(f"PostgreSQL connection health check failed: {e}")
        health_results["postgres"] = f"failed: {str(e)}"
        health_results["status"] = "unhealthy"

    # 2. Verify Redis Connection (Async)
    try:
        start_time = time.time()
        redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_timeout=2)
        ping_response = await redis_client.ping()
        await redis_client.close()
        if ping_response:
            latency = (time.time() - start_time) * 1000
            health_results["redis"] = f"connected ({latency:.2f}ms)"
        else:
            health_results["redis"] = "unhealthy (ping failed)"
            health_results["status"] = "unhealthy"
    except Exception as e:
        logger.error(f"Redis connection health check failed: {e}")
        health_results["redis"] = f"failed: {str(e)}"
        health_results["status"] = "unhealthy"

    # 3. Verify Qdrant Connection
    try:
        start_time = time.time()
        qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2)
        # Check basic collection list or simple health endpoint
        qdrant_client.get_collections()
        latency = (time.time() - start_time) * 1000
        health_results["qdrant"] = f"connected ({latency:.2f}ms)"
    except Exception as e:
        logger.error(f"Qdrant connection health check failed: {e}")
        health_results["qdrant"] = f"failed: {str(e)}"
        health_results["status"] = "unhealthy"

    if health_results["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=health_results
        )

    return health_results
