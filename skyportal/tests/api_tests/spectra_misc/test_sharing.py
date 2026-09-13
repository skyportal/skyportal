from skyportal.tests import api


def test_sharing_photometry(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    assert status == 400
    assert data["status"] == "error"
    assert "Cannot find photometry point with ID" in data["message"]

    status, data = api(
        "POST",
        "sharing",
        data={"photometryIDs": [photometry_id], "groupIDs": [public_group.id]},
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["obj_id"] == public_source.id


def test_sharing_photometry_with_foreign_group(
    upload_data_token,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token2,
    ztf_camera,
):
    public_source = public_source_two_groups
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token2
    )
    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    assert status == 400
    assert data["status"] == "error"
    assert "Cannot find photometry point with ID" in data["message"]

    status, data = api(
        "POST",
        "sharing",
        data={"photometryIDs": [photometry_id], "groupIDs": [public_group.id]},
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token2
    )
    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["obj_id"] == public_source.id


def test_cannot_share_unowned_photometry(
    upload_data_token,
    upload_data_token_two_groups,
    public_source,
    public_group,
    public_group2,
    view_only_token_group2,
    ztf_camera,
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        "sharing",
        data={"photometryIDs": [photometry_id], "groupIDs": [public_group2.id]},
        token=upload_data_token_two_groups,
    )

    assert status == 400
    assert data["status"] == "error"
    assert "owner" in data["message"].lower()


def test_system_admin_can_share_unowned_photometry(
    upload_data_token,
    super_admin_token,
    public_source,
    public_group,
    public_group2,
    view_only_token_group2,
    ztf_camera,
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "POST",
        "sharing",
        data={"photometryIDs": [photometry_id], "groupIDs": [public_group2.id]},
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token_group2
    )
    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    assert status == 200
    assert data["status"] == "success"


def _upload_photometry(token, obj_id, group_id, instrument_id):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(obj_id),
            "mjd": 58000.0,
            "instrument_id": instrument_id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [group_id],
        },
        token=token,
    )
    assert status == 200
    return data["data"]["ids"][0]


def test_can_share_grants_sharing_of_unowned_photometry(
    upload_data_token,
    upload_data_token_two_groups,
    user_two_groups,
    super_admin_token,
    public_source,
    public_group,
    public_group2,
    view_only_token_group2,
    ztf_camera,
):
    photometry_id = _upload_photometry(
        upload_data_token, public_source.id, public_group.id, ztf_camera.id
    )

    # Without `can_share_photometry` in the point's group, a non-owner is refused.
    status, data = api(
        "POST",
        "sharing",
        data={"photometryIDs": [photometry_id], "groupIDs": [public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 400
    assert data["status"] == "error"

    status, data = api(
        "PATCH",
        f"groups/{public_group.id}/users",
        data={"userID": user_two_groups.id, "canSharePhotometry": True},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "sharing",
        data={"photometryIDs": [photometry_id], "groupIDs": [public_group2.id]},
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token_group2
    )
    assert status == 200
    assert data["data"]["obj_id"] == public_source.id


def test_can_share_does_not_apply_to_spectra(
    upload_data_token_two_groups,
    user_two_groups,
    super_admin_token,
    public_source_spectrum,
    public_group,
    public_group2,
):
    status, data = api(
        "PATCH",
        f"groups/{public_group.id}/users",
        data={"userID": user_two_groups.id, "canSharePhotometry": True},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "sharing",
        data={
            "spectrumIDs": [public_source_spectrum.id],
            "groupIDs": [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 400
    assert data["status"] == "error"


def test_can_share_photometry_limited_to_own_groups(
    upload_data_token,
    upload_data_token_two_groups,
    user_two_groups,
    super_admin_token,
    public_source,
    public_group,
    public_group_no_streams,
    ztf_camera,
):
    photometry_id = _upload_photometry(
        upload_data_token, public_source.id, public_group.id, ztf_camera.id
    )

    status, data = api(
        "PATCH",
        f"groups/{public_group.id}/users",
        data={"userID": user_two_groups.id, "canSharePhotometry": True},
        token=super_admin_token,
    )
    assert status == 200

    # `user_two_groups` is not a member of `public_group_no_streams`, so it cannot
    # receive a point they do not own.
    status, data = api(
        "POST",
        "sharing",
        data={
            "photometryIDs": [photometry_id],
            "groupIDs": [public_group_no_streams.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "not a member of" in data["message"]

    # The owner is not restricted.
    status, data = api(
        "POST",
        "sharing",
        data={
            "photometryIDs": [photometry_id],
            "groupIDs": [public_group_no_streams.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
