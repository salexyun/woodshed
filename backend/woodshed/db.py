import os
from collections.abc import Iterator
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


@cache
def engine() -> Engine:
    # A short timeout lets /healthz answer 503 instead of hanging when Postgres is down.
    # Neon suspends idle databases and drops pooled connections, hence the pre-ping.
    # Bound parameters (the cue) would otherwise appear in exception text and then in logs.
    return create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"connect_timeout": 3},
        pool_pre_ping=True,
        hide_parameters=True,
    )


def get_session() -> Iterator[Session]:
    with Session(engine()) as session:
        yield session
