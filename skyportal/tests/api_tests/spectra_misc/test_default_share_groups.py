from skyportal.tests import api


def test_upload_without_groups_shares_with_uploader_only(
    upload_data_token, public_source, public_group, lris, user
):
    # With misc.share_data_with_public_group_by_default off (the default, and the
    # test config), a data product uploaded without group_ids is shared only with
    # the uploader's single-user group -- not the sitewide or any other group.
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": "2020-01-10T00:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.3, 232.1, 235.3],
        },
        token=upload_data_token,
    )
    assert status == 200, data
    spectrum_id = data["data"]["id"]

    status, data = api("GET", f"spectrum/{spectrum_id}", token=upload_data_token)
    assert status == 200, data
    group_ids = {g["id"] for g in data["data"]["groups"]}
    assert group_ids == {user.single_user_group.id}
    assert public_group.id not in group_ids
