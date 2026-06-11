from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.engine import get_async_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    maker = get_async_sessionmaker()
    async with maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
