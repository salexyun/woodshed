from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from woodshed.models import Base

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture
def alembic(database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(ALEMBIC_INI)
    yield config
    # Later integration tests rely on the schema, so always leave it at head.
    command.upgrade(config, "head")


@pytest.fixture
def engine(database_url):
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


def tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_head_creates_the_four_tables(alembic, engine):
    command.downgrade(alembic, "base")
    command.upgrade(alembic, "head")
    assert tables(engine) == {"profile", "item", "session", "rating"}


def test_migrated_schema_matches_the_models(alembic, engine):
    command.upgrade(alembic, "head")
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []


def test_downgrade_base_drops_every_table(alembic, engine):
    command.upgrade(alembic, "head")
    command.downgrade(alembic, "base")
    assert tables(engine) == set()
