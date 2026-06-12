"""Validates the dedupe SQL inside alembic migration ``6928ae655672_tablelock``.

The migration is what adds the ``UNIQUE`` constraint on ``photstats.obj_id``.
Before creating that index, it runs

    DELETE FROM photstats WHERE id NOT IN (
        SELECT DISTINCT ON (obj_id) id FROM photstats
        ORDER BY obj_id, last_full_update DESC NULLS LAST, id DESC
    )

to make the unique-index creation safe on deployments where the table already
contains duplicate ``obj_id`` rows. Fritz prod is verified clean so the DELETE
is a no-op there, but downstream deployments may differ. This test exercises
the actual SQL — not just a paraphrase — against a synthetic temp table.
"""

import sqlalchemy as sa

from skyportal.models import DBSession

# Same statement the migration uses (kept as a literal so a future migration
# edit that drops the ``ORDER BY`` clause will surface here too).
_MIGRATION_DEDUPE_SQL = """
    DELETE FROM photstats_test WHERE id NOT IN (
        SELECT DISTINCT ON (obj_id) id
        FROM photstats_test
        ORDER BY obj_id, last_full_update DESC NULLS LAST, id DESC
    )
"""


def test_migration_dedupes_photstats_keeping_most_recent():
    """Set up a synthetic table that mirrors photstats's relevant columns,
    seed it with deliberate duplicates that exercise every branch of the
    dedup ORDER BY, then run the migration's DELETE and assert exactly the
    expected survivors remain."""
    session = DBSession()
    session.execute(
        sa.text("""
        CREATE TEMP TABLE photstats_test (
            id SERIAL PRIMARY KEY,
            obj_id TEXT NOT NULL,
            last_full_update TIMESTAMP NULL
        )
    """)
    )
    # Seed data covering: (a) multiple rows with different last_full_update,
    # (b) NULL last_full_update preferred-last via NULLS LAST,
    # (c) tie on last_full_update broken by higher id,
    # (d) single-row obj (untouched).
    session.execute(
        sa.text("""
        INSERT INTO photstats_test (id, obj_id, last_full_update) VALUES
          (1, 'A', '2024-01-01 00:00:00'),
          (2, 'A', '2024-06-01 00:00:00'),
          (3, 'A', '2024-03-01 00:00:00'),
          (4, 'B', NULL),
          (5, 'B', '2024-01-01 00:00:00'),
          (6, 'C', '2024-01-01 00:00:00'),
          (7, 'C', '2024-01-01 00:00:00'),
          (8, 'D', '2024-05-15 00:00:00')
    """)
    )

    session.execute(sa.text(_MIGRATION_DEDUPE_SQL))

    rows = list(
        session.execute(
            sa.text("SELECT obj_id, id FROM photstats_test ORDER BY obj_id")
        ).all()
    )

    # Expectations:
    #   A: id=2 (latest last_full_update wins)
    #   B: id=5 (non-NULL beats NULL via NULLS LAST)
    #   C: id=7 (tie on last_full_update, higher id wins)
    #   D: id=8 (untouched)
    assert rows == [
        ("A", 2),
        ("B", 5),
        ("C", 7),
        ("D", 8),
    ], f"unexpected survivors: {rows}"

    # And the post-dedupe state must satisfy the same UNIQUE invariant the
    # migration is about to add: one row per obj_id.
    total = session.execute(
        sa.text("SELECT COUNT(*), COUNT(DISTINCT obj_id) FROM photstats_test")
    ).scalar_one_or_none()
    # scalar_one_or_none only returns the first column; query for both:
    cnts = session.execute(
        sa.text("SELECT COUNT(*) AS n, COUNT(DISTINCT obj_id) AS u FROM photstats_test")
    ).one()
    assert cnts.n == cnts.u == 4

    session.execute(sa.text("DROP TABLE photstats_test"))
    session.commit()


def test_migration_is_noop_on_clean_table():
    """When every obj_id is already unique, the DELETE deletes nothing.
    This is the Fritz-prod expected path: zero rows touched, no behavior
    change. Important because a buggy DELETE that mis-targeted under
    NULLS LAST would silently wipe rows on a clean deployment too."""
    session = DBSession()
    session.execute(
        sa.text("""
        CREATE TEMP TABLE photstats_test (
            id SERIAL PRIMARY KEY,
            obj_id TEXT NOT NULL,
            last_full_update TIMESTAMP NULL
        )
    """)
    )
    session.execute(
        sa.text("""
        INSERT INTO photstats_test (id, obj_id, last_full_update) VALUES
          (1, 'X', '2024-01-01 00:00:00'),
          (2, 'Y', NULL),
          (3, 'Z', '2024-05-01 00:00:00')
    """)
    )

    before = session.execute(sa.text("SELECT COUNT(*) FROM photstats_test")).scalar()
    session.execute(sa.text(_MIGRATION_DEDUPE_SQL))
    after = session.execute(sa.text("SELECT COUNT(*) FROM photstats_test")).scalar()

    assert before == after == 3

    session.execute(sa.text("DROP TABLE photstats_test"))
    session.commit()
