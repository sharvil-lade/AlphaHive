import os

os.environ["TESTING"] = "True"

import asyncio
import socket

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.session import engine_kwargs
from app.main import app
from app.models.models import Base


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    with socket.socket() as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


# Redis is an optional local container. Skipping (rather than failing) when it is
# absent keeps `pytest` honest: a red suite should mean broken code, not a service
# the developer chose not to boot.
requires_redis = pytest.mark.skipif(
    not _port_open(settings.REDIS_HOST, settings.REDIS_PORT),
    reason="Redis is not running (docker compose up -d redis)",
)


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """A fresh cookie jar per test — i.e. a distinct anonymous session."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session", autouse=True)
async def clean_database():
    """Flush Redis and make sure the schema exists before the suite runs."""
    if _port_open(settings.REDIS_HOST, settings.REDIS_PORT):
        from redis.asyncio import Redis

        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.flushdb()
        await redis_client.aclose()

    engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs())
    async with engine.begin() as conn:
        # sec_chunks.embedding is a pgvector column, so the type must exist first.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
