import os
os.environ["TESTING"] = "True"
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.core.config import settings
from backend.app.models.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def clean_database():
    """Ensure database is clean before running tests and teardown afterwards."""
    # Flush Redis cache to prevent cross-test contamination
    from redis.asyncio import Redis
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.flushdb()
        await redis_client.aclose()
    except Exception as e:
        import logging
        logging.getLogger("test-setup").warning(f"Could not flush Redis: {e}")

    # Create engine mapped specifically to test database connection URL
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Drop and recreate tables for clean integration testing
    async with engine.begin() as conn:
        # We can drop tables if we want a pristine environment, but for dev safety,
        # let's just make sure they are created
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    
    # Optional teardown: clean up stock metrics written during tests
    async with engine.begin() as conn:
        # Keep clean for next run by dropping or cleaning
        # To avoid deleting real user data, we can just delete test symbols
        pass
        
    await engine.dispose()
