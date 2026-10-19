"""Filtering a classification query by the origin that produced it."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

from skyportal.handlers.api.classification import filter_by_origin
from skyportal.models import Classification


def compiled(stmt):
    return str(
        stmt.compile(dialect=psql.dialect(), compile_kwargs={"literal_binds": True})
    )


def base():
    return sa.select(Classification.obj_id)


def test_a_single_origin_matches_without_regard_to_case():
    sql = compiled(filter_by_origin(base(), "ORACLE"))
    assert "lower(classifications.origin) IN ('oracle')" in sql


def test_several_origins_are_comma_separated():
    sql = compiled(filter_by_origin(base(), "ORACLE, FLARE"))
    assert "'oracle'" in sql and "'flare'" in sql


def test_no_origin_leaves_the_query_alone():
    # The parameter is optional, so an absent one must not narrow the results.
    for empty in (None, "", "  ", ","):
        assert compiled(filter_by_origin(base(), empty)) == compiled(base())


def test_an_origin_never_returns_the_classifications_without_one():
    # origin is nullable; lower(NULL) IN (...) is NULL, so those rows drop out
    # rather than matching every origin asked for.
    sql = compiled(filter_by_origin(base(), "ORACLE"))
    assert "IS NULL" not in sql
