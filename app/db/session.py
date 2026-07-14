from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import get_settings

settings = get_settings()

# Engine = kết nối vật lý đến PostgreSQL
# create_async_engine đọc DATABASE_URL từ .env để biết kết nối đến đâu
# echo=False: không in SQL ra terminal (đặt True khi debug)
engine = create_async_engine(
    settings.database_url,
    echo=False
)

# Session factory — mỗi lần gọi AsyncSessionLocal() sẽ tạo ra 1 session mới
# expire_on_commit=False: sau khi commit, object vẫn dùng được (quan trọng với async)
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False
)

# Engine đồng bộ — riêng cho agent tool functions.
# Azure AgentsClient gọi tool functions bằng function(**args) đồng bộ,
# không await — dùng AsyncSession ở đó sẽ không thực sự chạy query.
sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", "+psycopg2"),
    echo=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False,
)


# Hàm này FastAPI sẽ gọi mỗi khi có request cần dùng DB
# Dùng "async with" để đảm bảo session luôn được đóng sau khi dùng xong
# Dù có lỗi hay không — giống using() trong C#
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
        # yield thay vì return — FastAPI hiểu đây là dependency
        # code sau yield chạy sau khi endpoint xử lý xong (cleanup)