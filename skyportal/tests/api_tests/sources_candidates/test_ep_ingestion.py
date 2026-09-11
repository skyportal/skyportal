"""Tests for Einstein Probe data-center ingestion.

The EP service maps a data-center candidate onto a post_gcnevent_from_dictionary
payload: a cone localization from (ra, dec, pos_err), the EP numeric fields as a
GcnProperty, and trigger_id set to the EP candidate name so that later versions
of the same candidate land on the same GcnEvent instead of creating a new one.

That last part is the risky bit -- the dictionary path historically resolved
events by dateobs alone -- so it gets a dedicated test here.
"""

import uuid
from datetime import timedelta

import numpy as np

from skyportal.tests import api
from skyportal.utils.naive_datetime import utcnow_naive

RADIUS_MULTIPLIER = 1.0


def _ep_payload(
    name, group_ids, dateobs=None, ra=None, dec=None, pos_err=0.05, tag=None
):
    """Build the payload the EP service would post for one candidate."""
    if dateobs is None:
        dateobs = (
            utcnow_naive() - timedelta(seconds=int(np.random.randint(10**5, 10**7)))
        ).replace(microsecond=0)
    if ra is None:
        ra = float(np.random.uniform(0, 360))
    if dec is None:
        dec = float(np.random.uniform(-30, 30))

    error = pos_err * RADIUS_MULTIPLIER
    payload = {
        "dateobs": dateobs.isoformat(),
        "trigger_id": name,
        "aliases": [f"EP#{name}"],
        "skymap": {"ra": ra, "dec": dec, "error": error},
        "tags": ["EP", "X-ray"] + ([tag] if tag else []),
        "properties": {
            "ep_name": name,
            "ep_version": "1",
            "flux": 1.2e-10,
            "src_id": 3,
            "src_significance": 7.5,
            "bkg_counts": 2.0,
            "net_counts": 42.0,
            "net_rate": 0.35,
            "exp_time": 1200.0,
        },
        "group_ids": list(group_ids),
    }
    localization_name = f"{ra:.5f}_{dec:.5f}_{error:.5f}"
    return payload, dateobs, localization_name


def test_ep_candidate_creates_restricted_event(
    super_admin_token, public_group2, view_only_token, view_only_token_group2
):
    """An EP candidate becomes a GcnEvent readable only by the EP group."""
    name = f"EP{uuid.uuid4().hex[:10]}"
    payload, dateobs, localization_name = _ep_payload(name, [public_group2.id])

    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    dateobs_str = dateobs.strftime("%Y-%m-%d %H:%M:%S")

    status, data = api("GET", f"gcn_event/{dateobs_str}", token=view_only_token_group2)
    assert status == 200, data
    assert data["data"]["trigger_id"] == name
    assert "EP" in data["data"]["tags"]

    # the proprietary feed must not be visible outside the EP group
    status, data = api("GET", f"gcn_event/{dateobs_str}", token=view_only_token)
    assert status in (400, 403, 404), data

    # the cone localization was built from ra/dec/pos_err
    status, data = api(
        "GET",
        f"localization/{dateobs_str}/name/{localization_name}",
        token=view_only_token_group2,
    )
    assert status == 200, data


def test_ep_new_version_reuses_event_via_trigger_id(
    super_admin_token, public_group2, view_only_token_group2
):
    """A revised EP version lands on the same event, even if obs_start moved.

    EP can refine a candidate's position and its observation start between
    versions. Keyed on dateobs alone, each revision would spawn a separate
    GcnEvent; keyed on trigger_id (the EP name) it adds a localization to the
    existing one.
    """
    name = f"EP{uuid.uuid4().hex[:10]}"
    tag = str(uuid.uuid4())

    payload_v1, dateobs_v1, loc_v1 = _ep_payload(
        name, [public_group2.id], tag=tag, ra=10.0, dec=20.0, pos_err=0.05
    )
    status, data = api("POST", "gcn_event", data=payload_v1, token=super_admin_token)
    assert status == 200, data

    # version 2: refined position AND a shifted observation start
    payload_v2, _, loc_v2 = _ep_payload(
        name,
        [public_group2.id],
        dateobs=dateobs_v1 + timedelta(seconds=30),
        ra=10.01,
        dec=20.01,
        pos_err=0.02,
        tag=tag,
    )
    payload_v2["properties"]["ep_version"] = "2"
    status, data = api("POST", "gcn_event", data=payload_v2, token=super_admin_token)
    assert status == 200, data

    # exactly one event carries this candidate's tag -- v2 did not fork a new one
    status, data = api(
        "GET", "gcn_event", params={"gcnTagKeep": tag}, token=view_only_token_group2
    )
    assert status == 200, data
    events = data["data"]["events"]
    assert len(events) == 1, events
    assert events[0]["trigger_id"] == name

    # and the event keeps its original dateobs, with both localizations attached
    dateobs_str = dateobs_v1.strftime("%Y-%m-%d %H:%M:%S")
    for localization_name in (loc_v1, loc_v2):
        status, data = api(
            "GET",
            f"localization/{dateobs_str}/name/{localization_name}",
            token=view_only_token_group2,
        )
        assert status == 200, data


def test_ep_properties_recorded(
    super_admin_token, public_group2, view_only_token_group2
):
    """The EP numeric fields survive onto the event as a GcnProperty."""
    name = f"EP{uuid.uuid4().hex[:10]}"
    payload, dateobs, _ = _ep_payload(name, [public_group2.id])

    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    dateobs_str = dateobs.strftime("%Y-%m-%d %H:%M:%S")
    status, data = api("GET", f"gcn_event/{dateobs_str}", token=view_only_token_group2)
    assert status == 200, data

    properties = data["data"].get("properties") or []
    assert properties, data["data"]
    recorded = properties[0]["data"]
    assert recorded["ep_name"] == name
    assert recorded["ep_version"] == "1"
    assert recorded["net_counts"] == 42.0
    assert recorded["src_significance"] == 7.5


def test_restricted_ep_event_does_not_leak_position_as_source(
    super_admin_token, public_group2, view_only_token
):
    """A restricted EP event must not materialize a globally-readable Obj.

    post_gcn_source creates a source whenever the localization error is under
    SOURCE_RADIUS_THRESHOLD (8 arcmin). Real EP position errors are ~2-3 arcmin,
    so every EP candidate reaches that path. Obj.read is public in SkyPortal by
    design -- access control lives on Source and Candidate -- and the object id
    is derived from dateobs, so an auto-created object would hand the exact
    position of a restricted event to any user who can guess the id.
    """
    name = f"EP{uuid.uuid4().hex[:10]}"
    # mid-range of the real EP pos_err distribution (0.031-0.053 deg)
    payload, dateobs, _ = _ep_payload(name, [public_group2.id], pos_err=0.04)

    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    dateobs_str = dateobs.strftime("%Y-%m-%d %H:%M:%S")
    status, _ = api("GET", f"gcn_event/{dateobs_str}", token=view_only_token)
    assert status in (400, 403, 404), "the event itself should be hidden"

    stamp = dateobs.strftime("%y%m%d_%H%M%S")
    leaked = []
    for obj_id in (f"EP-{stamp}", f"GCN-{stamp}", f"GRB-{stamp}", stamp):
        status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
        if status == 200:
            leaked.append((obj_id, data["data"].get("ra"), data["data"].get("dec")))
    assert not leaked, f"restricted EP position exposed via object(s): {leaked}"
