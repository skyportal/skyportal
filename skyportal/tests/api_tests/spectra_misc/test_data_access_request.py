"""Asking for, and being given, data you cannot see.

`data_availability` deliberately reads past the access controls on photometry
and spectra, so these pin what it may say (metadata) and what it may not
(the data itself), and that a grant goes only through an answered request.
"""

import pytest

from skyportal.tests import api


def upload_hidden_photometry(
    obj_id, instrument_id, group_id, token, filter="ztfg", mjd=58000.0
):
    """Photometry belonging to one group only, as the owner sees it."""
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": mjd,
            "instrument_id": instrument_id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": filter,
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200
    return data["data"]["ids"][0]


def upload_hidden_spectrum(obj_id, instrument_id, group_id, token):
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": obj_id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": instrument_id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200
    return data["data"]["id"]


def test_availability_describes_hidden_photometry_but_not_its_values(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "GET", f"sources/{obj_id}/data_availability", token=view_only_token
    )
    assert status == 200
    photometry = data["data"]["photometry"]
    assert len(photometry) == 1
    dataset = photometry[0]
    assert dataset["filter"] == "ztfg"
    assert dataset["num_points"] == 1
    assert dataset["first_mjd"] == dataset["last_mjd"] == 58000.0
    assert dataset["owner"]["id"] == user_two_groups.id
    assert dataset["instrument"]["id"] == ztf_camera.id
    assert dataset["request"] is None
    # The point of the endpoint: it says the data is there, not what it says.
    assert "flux" not in dataset and "mag" not in dataset


def test_availability_omits_data_the_caller_can_already_see(
    upload_data_token,
    public_source,
    public_group,
    view_only_token,
    ztf_camera,
):
    upload_hidden_photometry(
        public_source.id, ztf_camera.id, public_group.id, upload_data_token
    )

    status, data = api(
        "GET", f"sources/{public_source.id}/data_availability", token=view_only_token
    )
    assert status == 200
    assert data["data"]["photometry"] == []


def test_accepting_a_request_shares_the_photometry(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    photometry_id = upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    assert status == 400

    status, data = api(
        "POST",
        "data_access_request",
        data={
            "objId": obj_id,
            "photometry": [
                {
                    "ownerID": user_two_groups.id,
                    "instrumentID": ztf_camera.id,
                    "filter": "ztfg",
                }
            ],
            "message": "Working on a paper on this source",
        },
        token=view_only_token,
    )
    assert status == 200
    request_id = data["data"]["ids"][0]

    status, data = api(
        "PATCH",
        f"data_access_request/{request_id}",
        data={"status": "accepted", "groupID": public_group.id},
        token=upload_data_token_two_groups,
    )
    assert status == 200

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    assert status == 200
    assert data["data"]["obj_id"] == obj_id

    # Nothing hidden left to ask for.
    status, data = api(
        "GET", f"sources/{obj_id}/data_availability", token=view_only_token
    )
    assert status == 200
    assert data["data"]["photometry"] == []


def test_declining_a_request_leaves_the_data_hidden(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    photometry_id = upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "POST",
        "data_access_request",
        data={
            "objId": obj_id,
            "photometry": [
                {
                    "ownerID": user_two_groups.id,
                    "instrumentID": ztf_camera.id,
                    "filter": "ztfg",
                }
            ],
        },
        token=view_only_token,
    )
    assert status == 200
    request_id = data["data"]["ids"][0]

    status, data = api(
        "PATCH",
        f"data_access_request/{request_id}",
        data={"status": "declined"},
        token=upload_data_token_two_groups,
    )
    assert status == 200

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    assert status == 400

    status, data = api(
        "GET", f"data_access_request/{request_id}", token=view_only_token
    )
    assert status == 200
    assert data["data"]["status"] == "declined"

    # Groups an answer could grant into, as the owner sees them: the ones they
    # share with the requester, never one the requester is not in.
    status, data = api(
        "GET",
        f"data_access_request/{request_id}",
        token=upload_data_token_two_groups,
    )
    assert status == 200
    shareable = [group["id"] for group in data["data"]["shareable_groups"]]
    assert public_group.id in shareable
    assert public_group2.id not in shareable


def test_a_bystander_cannot_answer_a_request(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token,
    upload_data_token_group2,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "POST",
        "data_access_request",
        data={
            "objId": obj_id,
            "photometry": [
                {
                    "ownerID": user_two_groups.id,
                    "instrumentID": ztf_camera.id,
                    "filter": "ztfg",
                }
            ],
        },
        token=view_only_token,
    )
    assert status == 200
    request_id = data["data"]["ids"][0]

    # A member of the group holding the data, but neither its owner nor an
    # admin of that group.
    status, data = api(
        "PATCH",
        f"data_access_request/{request_id}",
        data={"status": "accepted", "groupID": public_group.id},
        token=upload_data_token_group2,
    )
    assert status == 400
    assert "Insufficient permissions" in data["message"]


def test_a_request_cannot_be_granted_to_a_group_the_requester_is_not_in(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "POST",
        "data_access_request",
        data={
            "objId": obj_id,
            "photometry": [
                {
                    "ownerID": user_two_groups.id,
                    "instrumentID": ztf_camera.id,
                    "filter": "ztfg",
                }
            ],
        },
        token=view_only_token,
    )
    assert status == 200
    request_id = data["data"]["ids"][0]

    status, data = api(
        "PATCH",
        f"data_access_request/{request_id}",
        data={"status": "accepted", "groupID": public_group2.id},
        token=upload_data_token_two_groups,
    )
    assert status == 400
    assert "not a member" in data["message"]


def test_spectra_can_be_asked_for_and_granted(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token,
    lris,
):
    obj_id = public_source_two_groups.id
    spectrum_id = upload_hidden_spectrum(
        obj_id, lris.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "GET", f"sources/{obj_id}/data_availability", token=view_only_token
    )
    assert status == 200
    spectra = data["data"]["spectra"]
    assert [spectrum["id"] for spectrum in spectra] == [spectrum_id]
    assert spectra[0]["observed_at"].startswith("2020-01-10")
    # The photometry plot marks the epoch, and works in MJD.
    assert spectra[0]["observed_at_mjd"] == pytest.approx(58858.0)
    assert "fluxes" not in spectra[0] and "wavelengths" not in spectra[0]

    status, data = api("GET", f"spectrum/{spectrum_id}", token=view_only_token)
    assert status != 200

    status, data = api(
        "POST",
        "data_access_request",
        data={"objId": obj_id, "spectrumIDs": [spectrum_id]},
        token=view_only_token,
    )
    assert status == 200
    request_id = data["data"]["ids"][0]

    status, data = api(
        "PATCH",
        f"data_access_request/{request_id}",
        data={"status": "accepted", "groupID": public_group.id},
        token=upload_data_token_two_groups,
    )
    assert status == 200

    status, data = api("GET", f"spectrum/{spectrum_id}", token=view_only_token)
    assert status == 200
    assert data["data"]["obj_id"] == obj_id


def test_a_group_can_keep_its_data_out_of_discovery(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    view_only_token,
    super_admin_token,
    ztf_camera,
):
    """Data held only by a group that does not advertise is never mentioned."""
    obj_id = public_source_two_groups.id
    upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )

    status, data = api(
        "GET", f"sources/{obj_id}/data_availability", token=view_only_token
    )
    assert status == 200
    assert len(data["data"]["photometry"]) == 1

    status, data = api(
        "PUT",
        f"groups/{public_group2.id}",
        data={"name": public_group2.name, "discoverable_data": False},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{obj_id}/data_availability", token=view_only_token
    )
    assert status == 200
    assert data["data"]["photometry"] == []


def test_an_owner_can_keep_their_data_out_of_discovery(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )
    dataset = {
        "ownerID": user_two_groups.id,
        "instrumentID": ztf_camera.id,
        "filter": "ztfg",
    }

    status, data = api(
        "PATCH",
        "internal/profile",
        data={"preferences": {"hideDataFromDiscovery": True}},
        token=upload_data_token_two_groups,
    )
    assert status == 200

    status, data = api(
        "GET", f"sources/{obj_id}/data_availability", token=view_only_token
    )
    assert status == 200
    assert data["data"]["photometry"] == []

    # And it cannot be asked for by guessing at what is there.
    status, data = api(
        "POST",
        "data_access_request",
        data={"objId": obj_id, "photometry": [dataset]},
        token=view_only_token,
    )
    assert status == 400
    assert "No photometry to request" in data["message"]


def test_requests_are_paginated(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    filters = ["ztfg", "ztfr", "ztfi"]
    # Dedup keys on epoch rather than filter, so give each its own.
    for index, filter in enumerate(filters):
        upload_hidden_photometry(
            obj_id,
            ztf_camera.id,
            public_group2.id,
            upload_data_token_two_groups,
            filter=filter,
            mjd=58100.0 + index,
        )

    status, data = api(
        "POST",
        "data_access_request",
        data={
            "objId": obj_id,
            "photometry": [
                {
                    "ownerID": user_two_groups.id,
                    "instrumentID": ztf_camera.id,
                    "filter": filter,
                }
                for filter in filters
            ],
        },
        token=view_only_token,
    )
    assert status == 200
    assert len(data["data"]["ids"]) == 3

    status, data = api(
        "GET",
        "data_access_request?direction=outgoing&numPerPage=2&pageNumber=1",
        token=view_only_token,
    )
    assert status == 200
    assert data["data"]["totalMatches"] == 3
    first_page = [request["id"] for request in data["data"]["requests"]]
    assert len(first_page) == 2

    status, data = api(
        "GET",
        "data_access_request?direction=outgoing&numPerPage=2&pageNumber=2",
        token=view_only_token,
    )
    assert status == 200
    second_page = [request["id"] for request in data["data"]["requests"]]
    assert len(second_page) == 1
    assert not set(first_page) & set(second_page)


def test_asking_twice_for_the_same_dataset_is_refused(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    view_only_token,
    user_two_groups,
    ztf_camera,
):
    obj_id = public_source_two_groups.id
    upload_hidden_photometry(
        obj_id, ztf_camera.id, public_group2.id, upload_data_token_two_groups
    )
    request = {
        "objId": obj_id,
        "photometry": [
            {
                "ownerID": user_two_groups.id,
                "instrumentID": ztf_camera.id,
                "filter": "ztfg",
            }
        ],
    }

    status, data = api(
        "POST", "data_access_request", data=request, token=view_only_token
    )
    assert status == 200

    status, data = api(
        "POST", "data_access_request", data=request, token=view_only_token
    )
    assert status == 400
    assert "already asked" in data["message"]
