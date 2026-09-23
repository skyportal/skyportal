"""Loading users for a response must not drag in their other tables.

A spectrum names an owner, PIs, reducers and observers, so a handful of spectra
reaches dozens of users and anything loaded per user is paid for dozens of
times.
"""

import pytest
import sqlalchemy as sa
import yaml
from sqlalchemy.orm import Session, selectinload

import baselayer.app.psa  # noqa: F401  installs the social_auth backref
from skyportal.handlers.api.spectrum import user_columns_only
from skyportal.models import Group

# group_users is how Group.users is reached, so it is not an extra.
EXTRA_TABLES = ("usersocialauths", "roles", "acls")


@pytest.fixture()
def engine():
    cfg = yaml.safe_load(open("test_config.yaml")).get("database", {})
    url = sa.engine.URL.create(
        "postgresql+psycopg",
        username=cfg.get("user", "skyportal"),
        password=cfg.get("password") or None,
        host=cfg.get("host", "localhost"),
        port=cfg.get("port", 5432),
        database=cfg.get("database", "skyportal_test"),
    )
    engine = sa.create_engine(url)
    try:
        engine.connect().close()
    except sa.exc.OperationalError as exc:
        pytest.skip(f"no test database: {exc}")
    sa.orm.configure_mappers()
    yield engine
    engine.dispose()


def load_groups(engine, option):
    """The groups, and every statement run while loading them and their users."""
    seen = []

    def record(conn, cursor, statement, *rest):
        seen.append(" ".join(statement.split()))

    sa.event.listen(engine, "before_cursor_execute", record)
    try:
        with Session(engine) as session:
            groups = (
                session.scalars(sa.select(Group).options(option).limit(5))
                .unique()
                .all()
            )
            users = [user for group in groups for user in group.users]
    finally:
        sa.event.remove(engine, "before_cursor_execute", record)
    return users, seen


def test_a_user_loaded_for_a_response_costs_no_extra_queries(engine):
    _, queries = load_groups(engine, user_columns_only(selectinload(Group.users)))
    for table in EXTRA_TABLES:
        assert not [q for q in queries if table in q], table


def test_the_wildcard_it_replaces_loads_social_auth(engine):
    # Why the helper names the relationships instead: noload("*") cannot apply
    # to User.social_auth, which is lazy="dynamic", so the wildcard meant to
    # suppress per-user queries issues one per user instead.
    _, queries = load_groups(engine, selectinload(Group.users).noload("*"))
    assert [q for q in queries if "usersocialauths" in q]


def test_the_helper_leaves_the_user_columns_alone(engine):
    # Suppressing too much would empty the response rather than speed it up.
    users, _ = load_groups(engine, user_columns_only(selectinload(Group.users)))
    if not users:
        pytest.skip("no group members in the test database")
    assert all(user.username for user in users)


def test_nothing_reintroduces_the_wildcard():
    # It costs more than passing no option at all, so it must not come back.
    source = open("skyportal/handlers/api/spectrum.py").read()
    assert source.count('.noload("*")') == 0
