import uuid

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.gcn_events import GcnEventObjPost
from skyportal_py.sources import SourcePost

from skyportal.tests import api, client

# gcn_GW190814 fixture: dateobs 2019-08-14 21:10:39, localization
# "LALInference.v1.fits.gz".
LOCALIZATION_NAME = "LALInference.v1.fits.gz"


def _dateobs(gcn_event):
    return gcn_event.dateobs.strftime("%Y-%m-%dT%H:%M:%S")


def _post_source(token, ra=24.6258, dec=-32.9024):
    obj_id = str(uuid.uuid4())
    client(token).post_source(SourcePost(id=obj_id, ra=ra, dec=dec, redshift=3))
    return obj_id


def _confirm(token, dateobs, source_id, gcn_status="confirmed", **extra):
    body = {
        "localization_name": LOCALIZATION_NAME,
        "localization_cumprob": 0.95,
        "source_id": source_id,
        "status": gcn_status,
        "start_date": "2019-08-13T00:00:00",
        "end_date": "2019-08-16T00:00:00",
        **extra,
    }
    return client(token).post_gcn_event_source(dateobs, GcnEventObjPost(**body))


def test_confirm_get_patch_delete_lifecycle(
    super_admin_token, view_only_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)

    # confirm the source in the GCN
    result = _confirm(
        super_admin_token,
        dateobs,
        source_id,
        gcn_status="confirmed",
        explanation="in localization",
        notes="looks real",
    )
    assert result.id is not None

    # GET single via path
    entries = client(view_only_token).fetch_gcn_event_source(dateobs, source_id)
    assert len(entries) == 1
    assert entries[0].obj_id == source_id
    assert entries[0].status == "confirmed"
    assert entries[0].explanation == "in localization"
    assert entries[0].notes == "looks real"

    # GET list (no source filter) includes it
    entries = client(view_only_token).fetch_gcn_event_sources(dateobs)
    assert any(e.obj_id == source_id for e in entries)

    # associated_gcns lists the event while confirmed
    gcns = client(view_only_token).fetch_gcn_events_associated_with_source(source_id)
    assert dateobs in [d.replace(" ", "T") for d in gcns]

    # PATCH to rejected
    client(super_admin_token).update_gcn_event_source(dateobs, source_id, "rejected")

    entries = client(view_only_token).fetch_gcn_event_source(dateobs, source_id)
    assert entries[0].status == "rejected"

    # associated_gcns only returns confirmed associations -> now empty for it
    gcns = client(view_only_token).fetch_gcn_events_associated_with_source(source_id)
    assert dateobs not in [d.replace(" ", "T") for d in gcns]

    # DELETE
    client(super_admin_token).delete_gcn_event_source(dateobs, source_id)

    entries = client(view_only_token).fetch_gcn_event_source(dateobs, source_id)
    assert entries == []


def test_list_filters_by_sources_id_list(
    super_admin_token, view_only_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_a = _post_source(upload_data_token)
    source_b = _post_source(upload_data_token, ra=25.0, dec=-33.0)

    for sid in (source_a, source_b):
        _confirm(super_admin_token, dateobs, sid, gcn_status="confirmed")

    # full list has both
    entries = client(view_only_token).fetch_gcn_event_sources(dateobs)
    returned = {e.obj_id for e in entries}
    assert {source_a, source_b}.issubset(returned)

    # filter to just one via sourcesIDList
    entries = client(view_only_token).fetch_gcn_event_sources(
        dateobs, source_ids=[source_a]
    )
    returned = {e.obj_id for e in entries}
    assert returned == {source_a}


def test_post_requires_existing_localization(
    super_admin_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)
    with pytest.raises(SkyPortalError, match="Localization not found") as err:
        _confirm(
            super_admin_token,
            dateobs,
            source_id,
            gcn_status="confirmed",
            localization_name="does-not-exist.fits.gz",
        )
    assert err.value.status_code == 400


def test_post_missing_required_fields(
    super_admin_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)
    # omit localization_name/cumprob/dates -> validation error
    # raw api: intentionally incomplete payload the typed model can't produce
    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs}",
        data={"source_id": source_id, "status": "confirmed"},
        token=super_admin_token,
    )
    assert status == 400


def test_patch_unknown_source(super_admin_token, upload_data_token, gcn_GW190814):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)
    # never confirmed -> PATCH should fail
    with pytest.raises(SkyPortalError, match="not confirmed/rejected") as err:
        client(super_admin_token).update_gcn_event_source(
            dateobs, source_id, "rejected"
        )
    assert err.value.status_code == 400


def test_vetting_needs_only_access_to_the_event(
    super_admin_token, view_only_token, upload_data_token, gcn_GW190814
):
    """Vetting is not behind an ACL: whoever can see the event and the object
    can judge the association. A read-only token still cannot write."""
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)

    # a token that can post data, with no GCN-specific ACL, can vet
    _confirm(upload_data_token, dateobs, source_id, gcn_status="confirmed")

    entries = client(view_only_token).fetch_gcn_event_source(dateobs, source_id)
    assert entries[0].status == "confirmed"

    # read-only remains read-only
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).delete_gcn_event_source(dateobs, source_id)
    assert err.value.status_code == 401
