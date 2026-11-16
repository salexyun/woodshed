import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache

import psycopg
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


@contextmanager
def _primary_message_only() -> Iterator[None]:
    # A constraint violation's DETAIL quotes the row (the cue), and the error text
    # reaches spans and logs. Trimming below the psycopg instrumentation cleans it for
    # all of them. Data errors (e.g. 22P02) put the value in the primary message, and
    # errors raised by commit() (deferred constraints) bypass the cursor.
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
