import uuid

from skyportal.tests import api


def _make_group(super_admin_user, super_admin_token):
    status, data = api(
        "POST",
        "groups",
        data={"name": str(uuid.uuid4()), "group_admins": [super_admin_user.id]},
        token=super_admin_token,
    )
    assert status == 200, data
    return data["data"]["id"]


def _spectrum_group_ids(spectrum_id, token):
    status, data = api("GET", f"spectra/{spectrum_id}", token=token)
    assert status == 200, data
    return {g["id"] for g in data["data"]["groups"]}


def _photometry_group_ids(photometry_id, token):
    status, data = api("GET", f"photometry/{photometry_id}", token=token)
    assert status == 200, data
    return {g["id"] for g in data["data"]["groups"]}


def test_bulk_data_share_add_and_remove(
    super_admin_user,
    super_admin_token,
    upload_data_token,
    public_source,
    lris,
    ztf_camera,
):
    from_group = _make_group(super_admin_user, super_admin_token)
    to_group = _make_group(super_admin_user, super_admin_token)

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
            "group_ids": [from_group],
        },
        token=super_admin_token,
    )
    assert status == 200, data
    spectrum_id = data["data"]["id"]

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 59000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [from_group],
        },
        token=super_admin_token,
    )
    assert status == 200, data
    photometry_id = data["data"]["ids"][0]

    # not visible to the target group yet
    assert to_group not in _spectrum_group_ids(spectrum_id, super_admin_token)
    assert to_group not in _photometry_group_ids(photometry_id, super_admin_token)

    # a non-admin cannot bulk-share
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={"from_group_id": from_group, "to_group_id": to_group},
        token=upload_data_token,
    )
    assert status in (401, 403), data

    # add: share both data types with the target group
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={
            "from_group_id": from_group,
            "to_group_id": to_group,
            "data_types": ["spectra", "photometry"],
            "action": "add",
        },
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["counts"]["spectra"] >= 1
    assert data["data"]["counts"]["photometry"] >= 1

    assert to_group in _spectrum_group_ids(spectrum_id, super_admin_token)
    assert to_group in _photometry_group_ids(photometry_id, super_admin_token)

    # idempotent: a second add changes nothing
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={
            "from_group_id": from_group,
            "to_group_id": to_group,
            "action": "add",
        },
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["counts"]["spectra"] == 0
    assert data["data"]["counts"]["photometry"] == 0

    # remove: revoke the target group again
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={
            "from_group_id": from_group,
            "to_group_id": to_group,
            "action": "remove",
        },
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["counts"]["spectra"] >= 1
    assert to_group not in _spectrum_group_ids(spectrum_id, super_admin_token)
    assert to_group not in _photometry_group_ids(photometry_id, super_admin_token)


def test_bulk_data_share_rejects_bad_input(super_admin_user, super_admin_token):
    group = _make_group(super_admin_user, super_admin_token)

    # same source and target
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={"from_group_id": group, "to_group_id": group},
        token=super_admin_token,
    )
    assert status == 400, data

    # unknown data type
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={
            "from_group_id": group,
            "to_group_id": group + 1,
            "data_types": ["annotations"],
        },
        token=super_admin_token,
    )
    assert status == 400, data

    # neither from_group_id nor obj_ids
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={"to_group_id": group},
        token=super_admin_token,
    )
    assert status == 400, data

    # both from_group_id and obj_ids
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={"from_group_id": group, "to_group_id": group + 1, "obj_ids": ["x"]},
        token=super_admin_token,
    )
    assert status == 400, data


def test_bulk_data_share_by_obj_ids(
    super_admin_user, super_admin_token, public_source, lris, ztf_camera
):
    from_group = _make_group(super_admin_user, super_admin_token)
    to_group = _make_group(super_admin_user, super_admin_token)

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-02-01T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [1.0, 2.0, 3.0],
            "group_ids": [from_group],
        },
        token=super_admin_token,
    )
    assert status == 200, data
    spectrum_id = data["data"]["id"]

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 59050.0,
            "instrument_id": ztf_camera.id,
            "flux": 10.0,
            "fluxerr": 0.1,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [from_group],
        },
        token=super_admin_token,
    )
    assert status == 200, data
    photometry_id = data["data"]["ids"][0]

    # share by object, regardless of which group the data currently sits in
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={
            "obj_ids": [public_source.id],
            "to_group_id": to_group,
            "data_types": ["spectra", "photometry"],
            "action": "add",
        },
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"]["counts"]["spectra"] >= 1
    assert data["data"]["counts"]["photometry"] >= 1
    assert to_group in _spectrum_group_ids(spectrum_id, super_admin_token)
    assert to_group in _photometry_group_ids(photometry_id, super_admin_token)

    # remove by object
    status, data = api(
        "POST",
        "data_sharing/bulk",
        data={
            "obj_ids": [public_source.id],
            "to_group_id": to_group,
            "action": "remove",
        },
        token=super_admin_token,
    )
    assert status == 200, data
    assert to_group not in _spectrum_group_ids(spectrum_id, super_admin_token)
    assert to_group not in _photometry_group_ids(photometry_id, super_admin_token)


def test_remove_group_from_spectrum(
    super_admin_user, super_admin_token, public_source, lris
):
    group1 = _make_group(super_admin_user, super_admin_token)
    group2 = _make_group(super_admin_user, super_admin_token)

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-11T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [1.0, 2.0, 3.0],
            "group_ids": [group1, group2],
        },
        token=super_admin_token,
    )
    assert status == 200, data
    spectrum_id = data["data"]["id"]
    assert {group1, group2} <= _spectrum_group_ids(spectrum_id, super_admin_token)

    # remove one group
    status, data = api(
        "DELETE", f"spectra/{spectrum_id}/groups/{group2}", token=super_admin_token
    )
    assert status == 200, data
    gids = _spectrum_group_ids(spectrum_id, super_admin_token)
    assert group2 not in gids
    assert group1 in gids

    # peel off the remaining groups; the last one must be refused so the
    # spectrum is never left with no groups (spectra also carry an owner group)
    remaining = sorted(_spectrum_group_ids(spectrum_id, super_admin_token))
    for gid in remaining[:-1]:
        status, data = api(
            "DELETE", f"spectra/{spectrum_id}/groups/{gid}", token=super_admin_token
        )
        assert status == 200, data
    last = _spectrum_group_ids(spectrum_id, super_admin_token)
    assert len(last) == 1
    status, data = api(
        "DELETE",
        f"spectra/{spectrum_id}/groups/{next(iter(last))}",
        token=super_admin_token,
    )
    assert status == 400, data
