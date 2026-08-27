from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _is_hosted(url: str) -> bool:
    """True for a managed Postgres (Supabase et al.) rather than a local container."""
    return "supabase." in url or "sslmode=require" in url


def _is_transaction_pooler(url: str) -> bool:
    """Supavisor in transaction mode (port 6543) hands out a different backend
    connection per transaction, so server-side prepared statements never survive."""
    return ":6543" in url or "pooler.supabase.com" in url


def engine_kwargs() -> dict[str, Any]:
    """Connection settings shared by the app engine and Alembic."""
    url = settings.DATABASE_URL or ""
    connect_args: dict[str, Any] = {}
    kwargs: dict[str, Any] = {"echo": False, "future": True}

    if _is_hosted(url):
        # Managed Postgres refuses plaintext. "require" encrypts without pinning a CA,
        # which is what every Supabase connection string assumes.
        connect_args["ssl"] = "require"
        # Cloud databases drop idle connections; without this the first query after an
        # idle period fails instead of transparently reconnecting.
        kwargs["pool_pre_ping"] = True

    if _is_transaction_pooler(url):
        # asyncpg caches prepared statements by default, which breaks against a
        # transaction pooler with "prepared statement _pg_N already exists".
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
        # The pooler already pools; a second pool on top just holds connections open.
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

    if connect_args:
        kwargs["connect_args"] = connect_args
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for database sessions in FastAPI routes.

    Deliberately does NOT commit on teardown. Writes commit explicitly; a blanket
    teardown commit meant read-only requests also committed, and if that connection
    had dropped (a hosted DB across the internet) it raised *after* the response was
    already sent — surfacing as a 500 traceback on a request the client saw succeed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
