"""The home-page feed of structured extractions read out of GCN Circulars."""

from skyportal.tests import api


def _recent(token):
    status, data = api("GET", "internal/recent_gcn_extractions", token=token)
    assert status == 200, data
    return data["data"]


def test_recent_extractions_summarize_the_record(
    super_admin_token, public_gcn_event_extraction
):
    rows = _recent(super_admin_token)
    match = [r for r in rows if r["id"] == public_gcn_event_extraction.id]
    assert len(match) == 1, "the extraction should appear in the recent feed"

    row = match[0]
    assert row["origin"] == "test"
    assert row["circular_id"] == 12345
    # the widget renders these beneath the event they describe
    assert row["dateobs"] is not None
    assert row["summary"]["event_name"] == "GRB 260604C"
    # a record with no photometry summarizes to zero rather than failing
    assert row["summary"]["n_photometry"] == 0
    assert row["summary"]["bandpasses"] == []


def test_recent_extractions_are_readable_by_a_normal_user(
    view_only_token, public_gcn_event_extraction
):
    assert isinstance(_recent(view_only_token), list)
