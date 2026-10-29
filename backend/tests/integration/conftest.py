import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from woodshed.db import get_session
from woodshed.main import app


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set TEST_DATABASE_URL to the test database (see compose.yaml)")
    return url


def client_for(url: str) -> Iterator[TestClient]:
    engine = create_engine(url, connect_args={"connect_timeout": 1})

    def session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(database_url):
    yield from client_for(database_url)


@pytest.fixture
def unreachable_client(database_url):
    # Nothing listens on port 1, so the database is down for this client only.
    url = make_url(database_url).set(port=1)
    yield from client_for(url.render_as_string(hide_password=False))


@pytest.fixture(scope="session")
def migrated(database_url) -> None:
    config = Config(Path(__file__).parents[2] / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture
def db(database_url, migrated) -> Iterator[Session]:
    """A session on an empty, migrated database, for arranging and checking rows."""
    engine = create_engine(database_url)
    with Session(engine) as session:
        session.execute(text("TRUNCATE profile, item, session, rating"))
        session.commit()
        yield session
    engine.dispose()
