from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

_engine = None
_async_session = None


def _ensure_engine() -> None:
    global _engine, _async_session
    if _engine is not None:
        return
    url = DATABASE_URL
    if url is None:
        raise RuntimeError(
            "DATABASE_URL is not set. Create a .env file with DATABASE_URL=postgresql+asyncpg://..."
        )
    _engine = create_async_engine(url, echo=False)
    _async_session = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    _ensure_engine()
    return _async_session  # type: ignore[return-value]


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    maker = get_async_sessionmaker()
    async with maker() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, _async_session
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session = None
