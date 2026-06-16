import uuid

from skyportal.tests import api

# gcn_GW190814 fixture: dateobs 2019-08-14 21:10:39, localization
# "LALInference.v1.fits.gz".
LOCALIZATION_NAME = "LALInference.v1.fits.gz"


def _dateobs(gcn_event):
    return gcn_event.dateobs.strftime("%Y-%m-%dT%H:%M:%S")


def _post_source(token, ra=24.6258, dec=-32.9024):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": ra, "dec": dec, "redshift": 3},
        token=token,
    )
    assert status == 200, data
    return obj_id


def _confirm(token, dateobs, source_id, confirmed=True, **extra):
    body = {
        "localization_name": LOCALIZATION_NAME,
        "localization_cumprob": 0.95,
        "source_id": source_id,
        "confirmed": confirmed,
        "start_date": "2019-08-13T00:00:00",
        "end_date": "2019-08-16T00:00:00",
        **extra,
    }
    return api("POST", f"sources_in_gcn/{dateobs}", data=body, token=token)


def test_confirm_get_patch_delete_lifecycle(
    super_admin_token, view_only_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)

    # confirm the source in the GCN
    status, data = _confirm(
        super_admin_token,
        dateobs,
        source_id,
        confirmed=True,
        explanation="in localization",
        notes="looks real",
    )
    assert status == 200, data
    assert data["data"]["id"] is not None

    # GET single via path
    status, data = api(
        "GET", f"sources_in_gcn/{dateobs}/{source_id}", token=view_only_token
    )
    assert status == 200, data
    entries = data["data"]
    assert len(entries) == 1
    assert entries[0]["obj_id"] == source_id
    assert entries[0]["confirmed"] is True
    assert entries[0]["explanation"] == "in localization"
    assert entries[0]["notes"] == "looks real"

    # GET list (no source filter) includes it
    status, data = api("GET", f"sources_in_gcn/{dateobs}", token=view_only_token)
    assert status == 200, data
    assert any(e["obj_id"] == source_id for e in data["data"])

    # associated_gcns lists the event while confirmed
    status, data = api("GET", f"associated_gcns/{source_id}", token=view_only_token)
    assert status == 200, data
    assert dateobs in [d.replace(" ", "T") for d in data["data"]["gcns"]]

    # PATCH to rejected
    status, data = api(
        "PATCH",
        f"sources_in_gcn/{dateobs}/{source_id}",
        data={"confirmed": False},
        token=super_admin_token,
    )
    assert status == 200, data

    status, data = api(
        "GET", f"sources_in_gcn/{dateobs}/{source_id}", token=view_only_token
    )
    assert status == 200, data
    assert data["data"][0]["confirmed"] is False

    # associated_gcns only returns confirmed associations -> now empty for it
    status, data = api("GET", f"associated_gcns/{source_id}", token=view_only_token)
    assert status == 200, data
    assert dateobs not in [d.replace(" ", "T") for d in data["data"]["gcns"]]

    # DELETE
    status, data = api(
        "DELETE", f"sources_in_gcn/{dateobs}/{source_id}", token=super_admin_token
    )
    assert status == 200, data

    status, data = api(
        "GET", f"sources_in_gcn/{dateobs}/{source_id}", token=view_only_token
    )
    assert status == 200, data
    assert data["data"] == []


def test_list_filters_by_sources_id_list(
    super_admin_token, view_only_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_a = _post_source(upload_data_token)
    source_b = _post_source(upload_data_token, ra=25.0, dec=-33.0)

    for sid in (source_a, source_b):
        status, data = _confirm(super_admin_token, dateobs, sid, confirmed=True)
        assert status == 200, data

    # full list has both
    status, data = api("GET", f"sources_in_gcn/{dateobs}", token=view_only_token)
    assert status == 200, data
    returned = {e["obj_id"] for e in data["data"]}
    assert {source_a, source_b}.issubset(returned)

    # filter to just one via sourcesIDList
    status, data = api(
        "GET",
        f"sources_in_gcn/{dateobs}",
        params={"sourcesIDList": source_a},
        token=view_only_token,
    )
    assert status == 200, data
    returned = {e["obj_id"] for e in data["data"]}
    assert returned == {source_a}


def test_post_requires_existing_localization(
    super_admin_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)
    status, data = _confirm(
        super_admin_token,
        dateobs,
        source_id,
        confirmed=True,
        localization_name="does-not-exist.fits.gz",
    )
    assert status == 400
    assert "Localization not found" in data["message"]


def test_post_missing_required_fields(
    super_admin_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)
    # omit localization_name/cumprob/dates -> validation error
    status, data = api(
        "POST",
        f"sources_in_gcn/{dateobs}",
        data={"source_id": source_id, "confirmed": True},
        token=super_admin_token,
    )
    assert status == 400


def test_patch_unknown_source(super_admin_token, upload_data_token, gcn_GW190814):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)
    # never confirmed -> PATCH should fail
    status, data = api(
        "PATCH",
        f"sources_in_gcn/{dateobs}/{source_id}",
        data={"confirmed": False},
        token=super_admin_token,
    )
    assert status == 400
    assert "not confirmed/rejected" in data["message"]


def test_manage_gcns_permission_required(
    super_admin_token, view_only_token, upload_data_token, gcn_GW190814
):
    dateobs = _dateobs(gcn_GW190814)
    source_id = _post_source(upload_data_token)

    # view-only lacks "Manage GCNs" -> cannot confirm
    status, _ = _confirm(view_only_token, dateobs, source_id, confirmed=True)
    assert status == 401

    # but a privileged token can, and view-only can still read it
    status, data = _confirm(super_admin_token, dateobs, source_id, confirmed=True)
    assert status == 200, data
    status, _ = api(
        "DELETE", f"sources_in_gcn/{dateobs}/{source_id}", token=view_only_token
    )
    assert status == 401
