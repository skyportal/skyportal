import sqlalchemy as sa

from skyportal.enum_types import sqla_enum_types
from skyportal.model_util import refresh_enums
from skyportal.models import DBSession


def test_visible_enum_types_sees_the_schema():
    from skyportal.model_util import visible_enum_types

    with DBSession() as session:
        visible = visible_enum_types(session)
    assert {t.name for t in sqla_enum_types} <= visible


def test_visible_enum_types_follows_search_path():
    """`ALTER TYPE` resolves through search_path, so the check has to as well:
    a type that is not reachable unqualified must read as missing."""
    from skyportal.model_util import visible_enum_types

    session = DBSession()
    try:
        session.execute(sa.text("SET LOCAL search_path TO pg_temp"))
        assert visible_enum_types(session) == set()
    finally:
        session.rollback()


def test_refresh_enums_is_a_noop_when_types_are_missing():
    """An unmigrated database has no enum types; refreshing them must not be
    what takes the app's startup down."""
    session = DBSession()
    try:
        session.execute(sa.text("SET LOCAL search_path TO pg_temp"))
        refresh_enums()
    finally:
        session.rollback()


def test_refresh_enums_keeps_the_configured_labels():
    refresh_enums()
    with DBSession() as session:
        for type in sqla_enum_types:
            labels = set(
                session.scalars(
                    sa.text(
                        "SELECT enumlabel FROM pg_enum e "
                        "JOIN pg_type t ON t.oid = e.enumtypid "
                        "WHERE t.typname = :name"
                    ),
                    {"name": type.name},
                )
            )
            assert set(type.enums) <= labels, type.name
