"""Shape checks on the SQL that access control generates.

When a policy is asked for a subset of columns (``bulk_verify`` does it on every
commit, ``ComposedAccessControl`` for each of its sub-policies), the target table
must appear only once in the FROM clause: a cross join there matches every row,
so the policy grants the whole table.
"""

import warnings

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.compiler import FROM_LINTING

from baselayer.app.models import ComposedAccessControl, CustomUserAccessControl
from skyportal import models

MODES = ("create", "read", "update", "delete")


def _uses_custom_control(logic):
    if isinstance(logic, CustomUserAccessControl):
        return True
    if isinstance(logic, ComposedAccessControl):
        return any(_uses_custom_control(sub) for sub in logic.access_controls)
    return False


def _pk_columns(cls):
    mapper = sa.inspect(cls)
    return [
        getattr(cls, mapper.get_property_by_column(col).key)
        for col in mapper.primary_key
    ]


def _cases():
    cases = []
    for mapper in models.Base.registry.mappers:
        cls = mapper.class_
        if not hasattr(cls, "select"):
            continue
        for mode in MODES:
            if _uses_custom_control(getattr(cls, mode, None)):
                cases.append((cls, mode))
    return sorted(cases, key=lambda case: (case[0].__name__, case[1]))


CASES = _cases()


def _cartesian_products(stmt):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        stmt.compile(dialect=postgresql.dialect(), linting=FROM_LINTING)
    return [str(w.message) for w in caught if "cartesian product" in str(w.message)]


def test_cases_cover_the_custom_policies():
    assert CASES, "no model uses CustomUserAccessControl; these tests are stale"


@pytest.mark.parametrize(
    "cls, mode", CASES, ids=[f"{cls.__name__}-{mode}" for cls, mode in CASES]
)
def test_column_filtered_policy_has_no_cartesian_product(cls, mode, user):
    stmt = cls.select(user, mode=mode, columns=_pk_columns(cls))

    products = _cartesian_products(stmt)
    assert not products, (
        f"{cls.__name__}.{mode} grants every row when asked for columns only:\n  "
        + "\n  ".join(products)
    )


@pytest.mark.parametrize(
    "cls, mode", CASES, ids=[f"{cls.__name__}-{mode}" for cls, mode in CASES]
)
def test_column_filtered_policy_returns_the_requested_keys(cls, mode, user):
    pk_columns = _pk_columns(cls)
    stmt = cls.select(user, mode=mode, columns=pk_columns)

    assert set(stmt.subquery().c.keys()) == {col.key for col in pk_columns}
