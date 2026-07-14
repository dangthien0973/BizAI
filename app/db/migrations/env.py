import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

from app.db.base import Base
from app.models.tenant import Tenant  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.booking import Booking  # noqa: F401
from app.models.operating_hours import OperatingHours  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """
    Lấy DATABASE_URL từ environment variable trực tiếp.
    Không dùng get_settings() vì pydantic-settings có thể đọc .env file
    thay vì environment variable thật.
    Đổi asyncpg → psycopg2 vì Alembic cần sync driver.
    """
    url = os.environ.get("DATABASE_URL", "")

    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please set it in Railway Variables."
        )

    # Railway inject postgresql:// — đổi sang psycopg2
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres://", "postgresql://")

    return url


def run_migrations_offline() -> None:
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_sync_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()