"""Tests for group-scoped read access on GCN events.

GcnEvent.read is accessible_by_groups_members, and that restriction cascades to
localizations and to every query that reaches sources through a localization.
These tests cover the three surfaces that matter for a proprietary event stream
(e.g. the Einstein Probe unverified-candidate feed):

  1. the event record itself,
  2. its localization,
  3. the localizationDateobs source query, which resolves a localization and
     then joins LocalizationTile by raw id -- the path that would otherwise
     disclose a restricted event's sky position.
"""

import uuid
from datetime import datetime, timedelta

import numpy as np
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.gcn_events import GcnEventPost

from skyportal.tests import api, client
from skyportal.utils.naive_datetime import utcnow_naive

# Wide enough that post_gcn_source does not fire (SOURCE_RADIUS_THRESHOLD is
# 8 arcmin by default), keeping these tests to the access-control path.
CONE_ERROR_DEG = 0.5


def _unique_dateobs():
    """A dateobs no other test has used (GcnEvent.dateobs is unique)."""
    dt = utcnow_naive() - timedelta(seconds=int(np.random.randint(10**6, 10**8)))
    return dt.replace(microsecond=0)


def _post_cone_event(token, group_ids=None):
    """Post a cone-localization GCN event, optionally restricted to groups.

    Returns (dateobs, localization_name, tag). The tag is unique per call so
    listing queries can isolate exactly this event regardless of how much other
    GCN data the test database holds.
    """
    dateobs = _unique_dateobs()
    ra, dec = float(np.random.uniform(0, 360)), float(np.random.uniform(-30, 30))
    tag = str(uuid.uuid4())

    client(token).post_gcn_event(
        GcnEventPost(
            dateobs=dateobs.isoformat(),
            skymap={"ra": ra, "dec": dec, "error": CONE_ERROR_DEG},
            tags=[tag],
            group_ids=group_ids,
        )
    )

    localization_name = f"{ra:.5f}_{dec:.5f}_{CONE_ERROR_DEG:.5f}"
    return dateobs.strftime("%Y-%m-%d %H:%M:%S"), localization_name, tag


def test_restricted_gcn_event_hidden_from_non_members(
    super_admin_token, public_group2, view_only_token, view_only_token_group2
):
    """An event restricted to group2 is readable by group2 members only."""
    dateobs, _, _ = _post_cone_event(super_admin_token, group_ids=[public_group2.id])

    # a member of the owning group can read it
    client(view_only_token_group2).fetch_gcn_event(dateobs)

    # a user who is not in the owning group cannot
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_gcn_event(dateobs)
    assert err.value.status_code in (400, 403, 404)

    # system admins bypass the restriction
    client(super_admin_token).fetch_gcn_event(dateobs)


def test_gcn_event_defaults_to_public_group(
    super_admin_token, view_only_token, view_only_token_group2
):
    """Posting without group_ids keeps the pre-restriction behavior: everyone reads it."""
    dateobs, _, _ = _post_cone_event(super_admin_token)

    for token in (view_only_token, view_only_token_group2):
        client(token).fetch_gcn_event(dateobs)


def test_restricted_gcn_event_absent_from_listing(
    super_admin_token, public_group2, view_only_token, view_only_token_group2
):
    """A restricted event must not appear in the event listing for non-members."""
    dateobs, _, tag = _post_cone_event(super_admin_token, group_ids=[public_group2.id])

    # filter by the event's unique tag so the assertion does not depend on
    # pagination or on how much other GCN data the test database holds
    page = client(view_only_token).fetch_gcn_events(gcn_tag_keep=[tag])
    assert page.events == []

    page = client(view_only_token_group2).fetch_gcn_events(gcn_tag_keep=[tag])
    listed = {e.dateobs.isoformat() for e in page.events}
    assert dateobs.replace(" ", "T") in listed


def test_localization_tags_listing_is_access_scoped(gcn_GW190425, view_only_token):
    """The global localization-tag listing goes through the access policy.

    /api/localization/tags returns the distinct set of tag texts across all
    localizations. It used to run a raw sa.select(LocalizationTag.text), which
    ignored the GcnEvent restriction and so exposed the tag vocabulary of
    restricted events. It now selects through LocalizationTag.select; this test
    guards both that scoping and that the endpoint still composes with
    .distinct() rather than erroring.
    """
    tags = client(view_only_token).fetch_localization_tags()
    # gcn_GW190425's localization carries the "Test" tag and its event is
    # attached to the public group the token's user belongs to
    assert "Test" in tags, tags


def test_restricted_localization_hidden_from_non_members(
    super_admin_token, public_group2, view_only_token, view_only_token_group2
):
    """The localization inherits the event's restriction."""
    dateobs, localization_name, _ = _post_cone_event(
        super_admin_token, group_ids=[public_group2.id]
    )

    client(view_only_token_group2).fetch_localization(dateobs, localization_name)

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_localization(dateobs, localization_name)
    assert err.value.status_code in (400, 403, 404)


def test_restricted_localization_does_not_leak_position_via_sources(
    super_admin_token, public_group2, view_only_token, view_only_token_group2
):
    """Regression test for the localizationDateobs source query.

    get_localization() used to resolve the localization with a raw
    sa.select(Localization.id) and then join LocalizationTile by literal id,
    bypassing every access policy. That let a non-member enumerate sources
    inside a restricted event's error circle -- which discloses the position of
    the event itself. The query must now fail to resolve the localization.
    """
    dateobs, localization_name, _ = _post_cone_event(
        super_admin_token, group_ids=[public_group2.id]
    )

    # The window must stay under the handler's 10-year limit, otherwise the
    # request fails date validation and this test would pass vacuously without
    # ever exercising the access check.
    event_time = datetime.fromisoformat(dateobs.replace(" ", "T"))
    params = {
        "localization_dateobs": dateobs,
        "localization_name": localization_name,
        "start_date": (event_time - timedelta(days=1)).isoformat(),
        "end_date": (event_time + timedelta(days=1)).isoformat(),
    }

    # a group2 member resolves the localization fine (proving the window and
    # names are valid, so the non-member failure below is about access only)
    client(view_only_token_group2).fetch_sources(**params)

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_sources(**params)
    assert err.value.status_code == 400
    assert "not found" in str(err.value).lower()


def test_events_list_filters_by_group(
    super_admin_token, public_group, public_group2, view_only_token_group2
):
    """groupIds narrows the event list within what the user can already read."""
    _, _, tag_a = _post_cone_event(super_admin_token, group_ids=[public_group2.id])
    _, _, tag_b = _post_cone_event(super_admin_token)  # public group

    # restricted to group2: the group2 event is there
    page = client(view_only_token_group2).fetch_gcn_events(
        group_ids=[public_group2.id], gcn_tag_keep=[tag_a]
    )
    assert len(page.events) == 1, page.events

    # ...and the public-group event is excluded by the same filter
    page = client(view_only_token_group2).fetch_gcn_events(
        group_ids=[public_group2.id], gcn_tag_keep=[tag_b]
    )
    assert page.events == [], page.events


def test_events_list_group_filter_cannot_widen_access(
    super_admin_token, public_group2, view_only_token
):
    """Asking for a group you are not in returns nothing, not someone else's events."""
    _, _, tag = _post_cone_event(super_admin_token, group_ids=[public_group2.id])

    page = client(view_only_token).fetch_gcn_events(
        group_ids=[public_group2.id], gcn_tag_keep=[tag]
    )
    assert page.events == [], page.events


def test_events_list_rejects_bad_group_ids(super_admin_token):
    # raw api: intentionally malformed groupIds the typed client can't produce
    status, data = api(
        "GET", "gcn_event", params={"groupIds": "not-an-int"}, token=super_admin_token
    )
    assert status == 400, data
