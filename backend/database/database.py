"""
Async SQLAlchemy engine and session factory.
Uses aiosqlite for local development; swap DATABASE_URL in .env for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config.settings import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Called once at application startup."""
    # Import models so SQLAlchemy registers them before create_all
    import models.flight    # noqa: F401
    import models.user      # noqa: F401
    import models.booking   # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
