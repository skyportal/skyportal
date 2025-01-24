from skyportal.tests import api


def test_delete_obj_non_admin(
    manage_sources_token,
    public_obj,
    public_source_no_data,
    upload_data_token,
    ztf_camera,
    public_group,
):
    # A manage_sources_token user cannot delete an obj from ObjFactory since things
    # like Photometry and Comments are created with other users as authors/owners
    status, data = api("DELETE", f"objs/{public_obj.id}", token=manage_sources_token)
    assert status == 400
    assert (
        data["message"]
        == f"Please remove all associated spectra from object with ID {public_obj.id} before removing."
    )

    # Now start with a fresh Obj with no associated data, and post photometry to it
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source_no_data.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfi",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    photometry_id = data["data"]["ids"][0]

    # Since the owner is the upload_data_token user, the manage_sources_token user
    # won't be able to delete this Obj either
    status, data = api(
        "DELETE", f"objs/{public_source_no_data.id}", token=manage_sources_token
    )
    assert status == 400
    assert data["message"] in [
        f"Cannot find object with ID {public_source_no_data.id}.",
        f"Please remove all associated photometry from object with ID {public_source_no_data.id} before removing.",
    ]

    # Now delete the photometry blocking the delete
    status, data = api("DELETE", f"photometry/{photometry_id}", token=upload_data_token)
    assert status == 200

    # Now the manage_source_token user should be able to delete the Obj,
    # since they are a member of the group the associated Source is saved to,
    # that is the only data referencing the `public_source_no_data` Obj.
    status, _ = api(
        "DELETE", f"objs/{public_source_no_data.id}", token=manage_sources_token
    )
    assert status == 200


def test_delete_obj_system_admin(public_obj, super_admin_token):
    status, data = api("DELETE", f"objs/{public_obj.id}", token=super_admin_token)
    assert status == 400
    assert (
        data["message"]
        == f"Please remove all associated spectra from object with ID {public_obj.id} before removing."
    )
