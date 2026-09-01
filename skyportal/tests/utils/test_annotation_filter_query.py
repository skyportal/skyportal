"""The SQL built for `annotationsFilter` on the sources query.

Covers the two things that made the filter unusable for GCN crossmatch
annotations: their fields sit one level down, keyed by event, and the origin is
compared case-insensitively on the column but not on the input.
"""

from skyportal.handlers.api.sources import create_annotation_query

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
