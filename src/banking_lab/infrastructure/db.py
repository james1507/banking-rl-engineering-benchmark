from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from urllib.parse import urlparse

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from banking_lab.config import settings

RETRY_STATES = frozenset({"40001", "40P01", "55P03"})


def transient_database_error(exc: SQLAlchemyError) -> bool:
    if isinstance(exc, PoolTimeout):
        return True
    if not isinstance(exc, DBAPIError):
        return False
    state = getattr(exc.orig, "sqlstate", None)
    return (
        state is None or state in RETRY_STATES | {"57014", "57P01"} or str(state).startswith("08")
    )


def require_local(url: str, *, disposable: bool = False) -> None:
    parsed = urlparse(url.replace("postgresql+psycopg", "postgresql"))
    if parsed.hostname not in {"db", "localhost", "127.0.0.1", "postgres"}:
        raise ValueError("Database host must be explicitly local")
    if disposable and not (
        parsed.path.startswith("/lab_test_") or parsed.path.startswith("/lab_eval_")
    ):
        raise ValueError(
            "Destructive operations require lab_test_ or lab_eval_ disposable database"
        )


def build_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=settings().pool_size,
        max_overflow=0,
        pool_timeout=3,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 3,
            "options": "-c statement_timeout=10000 -c lock_timeout=3000",
        },
    )


@lru_cache
def engine() -> Engine:
    return build_engine(settings().database_url)


@contextmanager
def transaction(db: Engine) -> Iterator[Connection]:
    with db.begin() as connection:
        yield connection


def ready(db: Engine) -> bool:
    with db.connect() as c:
        return bool(
            c.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002"
        )
