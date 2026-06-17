from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import AppSettings


@dataclass(slots=True)
class DatabaseHandle:
    settings: AppSettings
    _engine: Engine | None = field(default=None, init=False, repr=False)
    _session_factory: sessionmaker[Session] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    def session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine(),
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    def _build_engine(self) -> Engine:
        engine_kwargs: dict[str, object] = {
            "echo": self.settings.database_echo,
            "pool_pre_ping": self.settings.database_pool_pre_ping,
        }
        parsed_url = make_url(self.settings.database_url)
        if parsed_url.drivername.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if parsed_url.database in {None, "", ":memory:"}:
                engine_kwargs["poolclass"] = StaticPool
        return create_engine(self.settings.database_url, **engine_kwargs)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def test_session(self) -> Iterator[Session]:
        connection = self.engine().connect()
        transaction = connection.begin()
        session = self.session_factory()(bind=connection)
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()

    def ping(self) -> None:
        with self.engine().connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
        self._session_factory = None


def build_database(settings: AppSettings | None = None) -> DatabaseHandle:
    return DatabaseHandle(settings or AppSettings.from_env())


__all__ = ["DatabaseHandle", "build_database"]
