import pytest
from sqlalchemy import DateTime

from woodshed.models import Base

COLUMNS = {
    "profile": {
        "id",
        "years_playing",
        "stuck_on",
        "cue",
        "weekly_goal_days",
        "timezone",
        "created_at",
    },
    "item": {"id", "kind", "box", "due_at", "reviews", "last_rated_at", "created_at"},
    "session": {"id", "action", "length", "started_at", "finished_at"},
    "rating": {
        "id",
        "session_id",
        "item_id",
        "value",
        "box_before",
        "box_after",
        "rated_at",
    },
}

TIMESTAMPS = [
    ("profile", "created_at"),
    ("item", "due_at"),
    ("item", "last_rated_at"),
    ("item", "created_at"),
    ("session", "started_at"),
    ("session", "finished_at"),
    ("rating", "rated_at"),
]

tables = Base.metadata.tables


def test_models_define_exactly_the_four_tables():
    assert set(tables) == set(COLUMNS)


@pytest.mark.parametrize("table", COLUMNS)
def test_table_has_the_spec_columns(table):
    assert {c.name for c in tables[table].columns} == COLUMNS[table]


@pytest.mark.parametrize(("table", "column"), TIMESTAMPS)
def test_timestamps_are_timezone_aware(table, column):
    type_ = tables[table].c[column].type
    assert isinstance(type_, DateTime) and type_.timezone


def test_item_id_is_a_string_key():
    assert tables["item"].c.id.type.python_type is str


@pytest.mark.parametrize(
    ("column", "target"), [("session_id", "session.id"), ("item_id", "item.id")]
)
def test_rating_references_its_session_and_item(column, target):
    fks = tables["rating"].c[column].foreign_keys
    assert {fk.target_fullname for fk in fks} == {target}
