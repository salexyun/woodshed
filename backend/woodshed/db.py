import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache

import psycopg
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


@contextmanager
def _primary_message_only() -> Iterator[None]:
    # Postgres's DETAIL quotes row values (the cue) and the error text reaches spans and
    # logs. Trimming here, below the psycopg instrumentation, covers every path at once.
    try:
        yield
    except psycopg.Error as e:
        if e.diag.message_primary:
            e.args = (e.diag.message_primary,)
        raise


class _Cursor(psycopg.Cursor):
    def execute(self, *args, **kwargs):
        with _primary_message_only():
            return super().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        with _primary_message_only():
            return super().executemany(*args, **kwargs)


@cache
def engine() -> Engine:
    # A short timeout lets /healthz answer 503 instead of hanging when Postgres is down.
    # Neon suspends idle databases and drops pooled connections, hence the pre-ping.
    # Bound parameters (the cue) would otherwise appear in exception text and then in logs.
    return create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"connect_timeout": 3, "cursor_factory": _Cursor},
        pool_pre_ping=True,
        hide_parameters=True,
    )


def get_session() -> Iterator[Session]:
    with Session(engine()) as session:
        yield session
