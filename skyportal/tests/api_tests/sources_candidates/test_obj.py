import pytest
from skyportal_py import SkyPortalError
from skyportal_py.photometry import PhotometryPost

from skyportal.tests import client


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
    sp_manage = client(manage_sources_token)
    with pytest.raises(SkyPortalError) as err:
        sp_manage.delete_obj(public_obj.id)
    assert err.value.status_code == 400
    assert (
        str(err.value)
        == f"Please remove all associated spectra from object with ID {public_obj.id} before removing."
    )

    # Now start with a fresh Obj with no associated data, and post photometry to it
    sp_upload = client(upload_data_token)
    photometry_id = sp_upload.post_photometry(
        PhotometryPost(
            obj_id=str(public_source_no_data.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfi",
            group_ids=[public_group.id],
        )
    ).ids[0]

    # Since the owner is the upload_data_token user, the manage_sources_token user
    # won't be able to delete this Obj either
    with pytest.raises(SkyPortalError) as err:
        sp_manage.delete_obj(public_source_no_data.id)
    assert err.value.status_code == 400
    assert str(err.value) in [
        f"Cannot find object with ID {public_source_no_data.id}.",
        f"Please remove all associated photometry from object with ID {public_source_no_data.id} before removing.",
    ]

    # Now delete the photometry blocking the delete
    sp_upload.delete_photometry(photometry_id)

    # Now the manage_source_token user should be able to delete the Obj,
    # since they are a member of the group the associated Source is saved to,
    # that is the only data referencing the `public_source_no_data` Obj.
    sp_manage.delete_obj(public_source_no_data.id)


def test_delete_obj_system_admin(public_obj, super_admin_token):
    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).delete_obj(public_obj.id)
    assert err.value.status_code == 400
    assert (
        str(err.value)
        == f"Please remove all associated spectra from object with ID {public_obj.id} before removing."
    )
