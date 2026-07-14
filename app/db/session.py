import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


def get_async_url() -> str:
    """Lấy DATABASE_URL và đảm bảo dùng asyncpg driver."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Fallback cho local dev
        url = "postgresql+asyncpg://bizagent:bizagent_dev@localhost:5432/bizagent"
    # Railway inject postgresql:// — đổi sang asyncpg
    url = url.replace("postgres://", "postgresql://")
    if "+asyncpg" not in url and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


def get_sync_url() -> str:
    """Lấy DATABASE_URL với psycopg2 driver cho sync operations."""
    url = get_async_url()
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


# Async engine — dùng cho FastAPI endpoints
engine = create_async_engine(get_async_url(), echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Sync engine — dùng cho Azure AI Foundry tool functions
sync_engine = create_engine(get_sync_url(), echo=False)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session