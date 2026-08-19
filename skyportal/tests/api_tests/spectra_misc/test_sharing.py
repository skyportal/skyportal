import pytest
from skyportal_py import SkyPortalError
from skyportal_py.photometry import PhotometryPost

from skyportal.tests import client


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
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group2.id],
        )
    ).ids[0]

    sp.fetch_photometry_point(photometry_id, format="flux")

    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    with pytest.raises(
        SkyPortalError, match="Cannot find photometry point with ID"
    ) as err:
        client(view_only_token).fetch_photometry_point(photometry_id, format="flux")
    assert err.value.status_code == 400

    sp.post_sharing([public_group.id], photometry_ids=[photometry_id])

    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    point = client(view_only_token).fetch_photometry_point(photometry_id, format="flux")
    assert point.obj_id == public_source.id


def test_sharing_photometry_with_foreign_group(
    upload_data_token,
    public_source_two_groups,
    public_group,
    public_group2,
    view_only_token2,
    ztf_camera,
):
    public_source = public_source_two_groups
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group2.id],
        )
    ).ids[0]

    sp.fetch_photometry_point(photometry_id, format="flux")

    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    with pytest.raises(
        SkyPortalError, match="Cannot find photometry point with ID"
    ) as err:
        client(view_only_token2).fetch_photometry_point(photometry_id, format="flux")
    assert err.value.status_code == 400

    sp.post_sharing([public_group.id], photometry_ids=[photometry_id])

    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    point = client(view_only_token2).fetch_photometry_point(
        photometry_id, format="flux"
    )
    assert point.obj_id == public_source.id


def test_cannot_share_unowned_photometry(
    upload_data_token,
    upload_data_token_two_groups,
    public_source,
    public_group,
    public_group2,
    view_only_token_group2,
    ztf_camera,
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    sp.fetch_photometry_point(photometry_id, format="flux")

    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_two_groups).post_sharing(
            [public_group2.id], photometry_ids=[photometry_id]
        )
    assert err.value.status_code == 400
    assert "owner" in str(err.value).lower()


def test_system_admin_can_share_unowned_photometry(
    upload_data_token,
    super_admin_token,
    public_source,
    public_group,
    public_group2,
    view_only_token_group2,
    ztf_camera,
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    sp.fetch_photometry_point(photometry_id, format="flux")

    client(super_admin_token).post_sharing(
        [public_group2.id], photometry_ids=[photometry_id]
    )

    # `view_only_token only` belongs to `public_group`, but not `public_group2`
    client(view_only_token_group2).fetch_photometry_point(photometry_id, format="flux")


def _upload_photometry(token, obj_id, group_id, instrument_id):
    return (
        client(token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(obj_id),
                mjd=58000.0,
                instrument_id=instrument_id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[group_id],
            )
        )
        .ids[0]
    )


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
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_two_groups).post_sharing(
            [public_group2.id], photometry_ids=[photometry_id]
        )
    assert err.value.status_code == 400

    client(super_admin_token).update_group_user(
        public_group.id, user_two_groups.id, can_share_photometry=True
    )

    client(upload_data_token_two_groups).post_sharing(
        [public_group2.id], photometry_ids=[photometry_id]
    )

    point = client(view_only_token_group2).fetch_photometry_point(
        photometry_id, format="flux"
    )
    assert point.obj_id == public_source.id


def test_can_share_does_not_apply_to_spectra(
    upload_data_token_two_groups,
    user_two_groups,
    super_admin_token,
    public_source_spectrum,
    public_group,
    public_group2,
):
    client(super_admin_token).update_group_user(
        public_group.id, user_two_groups.id, can_share_photometry=True
    )

    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_two_groups).post_sharing(
            [public_group2.id], spectrum_ids=[public_source_spectrum.id]
        )
    assert err.value.status_code == 400


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

    client(super_admin_token).update_group_user(
        public_group.id, user_two_groups.id, can_share_photometry=True
    )

    # `user_two_groups` is not a member of `public_group_no_streams`, so it cannot
    # receive a point they do not own.
    with pytest.raises(SkyPortalError, match="not a member of") as err:
        client(upload_data_token_two_groups).post_sharing(
            [public_group_no_streams.id], photometry_ids=[photometry_id]
        )
    assert err.value.status_code == 400

    # The owner is not restricted.
    client(upload_data_token).post_sharing(
        [public_group_no_streams.id], photometry_ids=[photometry_id]
    )
