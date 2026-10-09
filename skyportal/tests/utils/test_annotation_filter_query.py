"""The SQL built for `annotationsFilter` on the sources query.

Covers the two things that made the filter unusable for GCN crossmatch
annotations: their fields sit one level down, keyed by event, and the origin is
compared case-insensitively on the column but not on the input.
"""

import asyncio

from skyportal.handlers.api.sources import (
    _annotation_filter_hint,
    create_annotation_query,
)

ORIGIN = ["GCN-crossmatch"]
DATEOBS = "2026-08-18T16:50:49"


def test_matches_fields_nested_under_an_event():
    # A crossmatch annotation is {event: {delta_t: ...}}, so a top-level lookup
    # alone finds nothing.
    sql, _ = create_annotation_query(
        ["delta_t", "-10", "ge"], ORIGIN, None, None, 0, is_admin=True
    )
    assert "jsonb_each" in sql


def test_scopes_to_the_named_event():
    # Without this a value from another event could hide a source from the list
    # it belongs to.
    sql, params = create_annotation_query(
        ["delta_t", "-10", "ge"],
        ORIGIN,
        None,
        None,
        0,
        is_admin=True,
        localization_dateobs=DATEOBS,
    )
    assert "dateobs" in sql
    assert any(p.value == DATEOBS for p in params)


def test_unscoped_when_no_event_is_named():
    sql, _ = create_annotation_query(
        ["delta_t", "-10", "ge"], ORIGIN, None, None, 0, is_admin=True
    )
    assert "dateobs" not in sql


def test_origin_is_lowered_to_match_the_column():
    _, params = create_annotation_query(
        ["delta_t", "-10", "ge"], ORIGIN, None, None, 0, is_admin=True
    )
    assert "gcn-crossmatch" in [p.value for p in params]


def test_non_numeric_values_are_not_cast():
    # `dateobs` is a string; casting it would error the whole query rather than
    # simply not matching.
    sql, _ = create_annotation_query(
        ["delta_t", "-10", "ge"], ORIGIN, None, None, 0, is_admin=True
    )
    assert "~ '^-?[0-9]" in sql


def test_group_restriction_applies_to_non_admins():
    sql, params = create_annotation_query(
        ["delta_t", "-10", "ge"],
        ORIGIN,
        None,
        None,
        0,
        is_admin=False,
        accessible_group_ids=[7, 9],
    )
    assert "group_annotations" in sql
    assert {7, 9} <= {p.value for p in params}


def test_no_readable_groups_matches_nothing():
    # An empty IN list is not valid SQL, and the user can read no annotations.
    sql, _ = create_annotation_query(
        ["delta_t", "-10", "ge"],
        ORIGIN,
        None,
        None,
        0,
        is_admin=False,
        accessible_group_ids=[],
    )
    assert "and false" in sql


def test_admin_skips_the_group_restriction():
    sql, _ = create_annotation_query(
        ["delta_t", "-10", "ge"], ORIGIN, None, None, 0, is_admin=True
    )
    assert "group_annotations" not in sql


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return [(r,) for r in self._rows]


class _FakeSession:
    """Answers the hint's key survey with a fixed set of annotations."""

    def __init__(self, rows):
        self._rows = rows

    async def execute(self, *args, **kwargs):
        return _FakeResult(self._rows)


# A crossmatch annotation: one entry per event, fields one level down.
EP_ANNOTATION = {
    "ep11900858886wxt14s2": {
        "age": 3189.19,
        "delta_t": 10.4,
        "ndethist": 181,
        "sgscore": 0.5,
    }
}


def test_no_hint_when_the_key_exists():
    # Nothing was wrong with the query, so the empty result is about the sky.
    hint = asyncio.run(
        _annotation_filter_hint(
            _FakeSession([EP_ANNOTATION]), ["delta_t: -10: ge"], ["gcn-crossmatch"]
        )
    )
    assert hint is None


def test_hint_names_the_missing_key_and_what_exists():
    hint = asyncio.run(
        _annotation_filter_hint(
            _FakeSession([EP_ANNOTATION]), ["deltat: -10: ge"], ["gcn-crossmatch"]
        )
    )
    assert "deltat" in hint
    assert "delta_t" in hint
    # The reason a top-level filter finds nothing is the nesting; say so.
    assert "nested" in hint


def test_hint_when_the_origin_has_no_annotations():
    hint = asyncio.run(
        _annotation_filter_hint(_FakeSession([]), ["delta_t"], ["not-an-origin"])
    )
    assert "not-an-origin" in hint


def test_no_hint_without_an_annotation_filter():
    # An empty result from an unrelated query is not the hint's business.
    assert (
        asyncio.run(_annotation_filter_hint(_FakeSession([EP_ANNOTATION]), None, None))
        is None
    )


def _jsonpath_params(params):
    return [p.value for p in params if "jsonpath" in p.key]


def test_the_nested_search_is_gated_on_a_jsonpath():
    # Expanding every annotation's data to reach the nested fields is what made
    # this unusable over the whole table, so the sub-objects are only expanded
    # for rows a jsonpath says could carry the field.
    sql, params = create_annotation_query(
        ["delta_t", "-10", "ge"], ORIGIN, None, None, 0, is_admin=True
    )
    assert "@? CAST(:annotations_filter_jsonpath_0 AS jsonpath)" in sql
    assert _jsonpath_params(params) == ['$.*."delta_t"']
    # The gate is a precondition on the original test, never a replacement.
    assert "jsonb_each" in sql


def test_the_existence_check_is_gated_too():
    sql, params = create_annotation_query(
        ["alma-archive"], None, None, None, 0, is_admin=True
    )
    assert "@? CAST(:annotations_filter_jsonpath_0 AS jsonpath)" in sql
    assert _jsonpath_params(params) == ['$.*."alma-archive"']


def test_a_field_name_cannot_reshape_the_jsonpath():
    # The name reaches the path as a quoted literal, so quotes in it are escaped
    # rather than closing the string and appending a predicate of their own.
    sql, params = create_annotation_query(
        ['a"] ? (1==1) ; $."b'], None, None, None, 0, is_admin=True
    )
    (path,) = _jsonpath_params(params)
    assert path == '$.*."a\\"] ? (1==1) ; $.\\"b"'
    # and the name itself is still bound, never interpolated into the SQL
    assert 'a"]' not in sql
