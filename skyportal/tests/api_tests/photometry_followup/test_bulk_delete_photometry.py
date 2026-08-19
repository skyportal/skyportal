from skyportal_py.photometry import PhotometryPost

from skyportal.tests import client


def test_bulk_delete_photometry(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    resp = client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=[58000.0, 58001.0, 58002.0],
            instrument_id=ztf_camera.id,
            flux=[12.24, 12.52, 12.70],
            fluxerr=[0.031, 0.029, 0.030],
            filter=["ztfg", "ztfg", "ztfg"],
            zp=[25.0, 25.0, 25.0],
            magsys=["ab", "ab", "ab"],
            group_ids=[public_group.id],
        )
    )
    upload_id = resp.upload_id

    result = client(super_admin_token).bulk_delete_photometry(upload_id)
    assert result == "Deleted 3 photometry point(s)."
