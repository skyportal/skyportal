import pytest
from skyportal_py import SkyPortalError
from skyportal_py.photometry import PhotometryPost

from skyportal.tests import api, assert_api_fail, client


def test_add_and_retrieve_annotation_group_id(
    annotation_token, upload_data_token, public_source, public_group, ztf_camera
):
    photometry_id = (
        client(upload_data_token)
        .post_photometry(
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
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    # try posting without an origin...
    # raw api: intentionally malformed payload the typed client can't produce (missing origin)
    status, data = api(
        "POST",
        f"photometry/{photometry_id}/annotations",
        data={
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert_api_fail(status, data, 400, "origin: Field required")

    # this should not work, since "origin" is empty
    # raw api: intentionally malformed payload the typed client can't produce (empty origin)
    status, data = api(
        "POST",
        f"photometry/{photometry_id}/annotations",
        data={
            "origin": "",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )

    assert status in [400, 401]
    assert "origin: String should match pattern" in data["message"]

    # first time adding an annotation to this object from Kowalski
    annotation_id = (
        client(annotation_token)
        .post_annotation(
            photometry_id,
            "kowalski",
            {"offset_from_host_galaxy": 1.5},
            resource_type="photometry",
            group_ids=[public_group.id],
        )
        .annotation_id
    )

    # this should not work, since "origin" Kowalski was already posted to this object
    # instead, try updating the existing annotation if you have new information!
    with pytest.raises(
        SkyPortalError, match="duplicate key value violates unique constraint"
    ) as err:
        client(annotation_token).post_annotation(
            photometry_id,
            "kowalski",
            {"offset_from_host_galaxy": 1.5},
            resource_type="photometry",
            group_ids=[public_group.id],
        )
    assert err.value.status_code in [500, 400]

    annotation = client(annotation_token).fetch_annotation(
        photometry_id, annotation_id, resource_type="photometry"
    )
    assert annotation.data["offset_from_host_galaxy"] == 1.5


def test_add_and_retrieve_annotation_group_access(
    annotation_token_two_groups,
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
    ztf_camera,
):
    sp_two_groups = client(annotation_token_two_groups)
    sp = client(annotation_token)
    photometry_id = (
        client(upload_data_token_two_groups)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source_two_groups.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group2.id],
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    annotation_id = sp_two_groups.post_annotation(
        photometry_id,
        "IPAC",
        {"distance_from_host": 7.4},
        resource_type="photometry",
        group_ids=[public_group2.id],
    ).annotation_id

    # This token belongs to public_group2
    annotation = sp_two_groups.fetch_annotation(
        photometry_id, annotation_id, resource_type="photometry"
    )
    assert annotation.data["distance_from_host"] == 7.4

    # This token does not belong to public_group2
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(photometry_id, annotation_id, resource_type="photometry")
    assert err.value.status_code == 403

    # Both tokens should be able to view this annotation, but not the underlying photometry
    annotation_id = sp_two_groups.post_annotation(
        photometry_id,
        "kowalski",
        {"ACAI_class": "type Ia"},
        resource_type="photometry",
        group_ids=[public_group.id, public_group2.id],
    ).annotation_id

    annotation = sp_two_groups.fetch_annotation(
        photometry_id, annotation_id, resource_type="photometry"
    )
    assert annotation.data["ACAI_class"] == "type Ia"

    # the underlying photometry is not accessible to group1
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(photometry_id, annotation_id, resource_type="photometry")
    assert err.value.status_code == 403

    # post new photometry with an annotation, open to both groups
    photometry_id = (
        client(upload_data_token_two_groups)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source_two_groups.id),
                mjd=58001.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id, public_group2.id],
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    annotation_id = sp_two_groups.post_annotation(
        photometry_id,
        "kowalski",
        {"ACAI_class": "type Ia"},
        resource_type="photometry",
        group_ids=[public_group2.id],
    ).annotation_id

    # token for group1 can view the photometry but cannot see the annotation
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(photometry_id, annotation_id, resource_type="photometry")
    assert err.value.status_code == 403

    # Both tokens should be able to view annotation after updating group list
    sp_two_groups.update_annotation(
        photometry_id,
        annotation_id,
        {"ACAI_class": "type IIn"},
        resource_type="photometry",
        group_ids=[public_group.id, public_group2.id],
    )

    # the new annotation on the new photometry should now accessible
    annotation = sp.fetch_annotation(
        photometry_id, annotation_id, resource_type="photometry"
    )
    assert annotation.data["ACAI_class"] == "type IIn"


def test_cannot_add_annotation_without_permission(
    view_only_token, upload_data_token, public_source, ztf_camera
):
    photometry_id = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids="all",
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    # raw api: intentionally malformed request (singular "annotation" route) the typed client can't produce
    status, data = api(
        "POST",
        f"photometry/{photometry_id}/annotation",
        data={"origin": "kowalski", "data": {"gaia_G": 14.5}},
        token=view_only_token,
    )
    assert status in [401, 405]
    assert data["status"] == "error"


def test_delete_annotation(
    annotation_token, upload_data_token, public_source, ztf_camera
):
    sp = client(annotation_token)
    photometry_id = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids="all",
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    annotation_id = sp.post_annotation(
        photometry_id, "kowalski", {"gaia_G": 14.5}, resource_type="photometry"
    ).annotation_id

    annotation = sp.fetch_annotation(
        photometry_id, annotation_id, resource_type="photometry"
    )
    assert annotation.data["gaia_G"] == 14.5

    # try to delete using the wrong photometry ID
    with pytest.raises(
        SkyPortalError,
        match="Annotation resource ID does not match resource ID given in path",
    ) as err:
        sp.delete_annotation(
            photometry_id + 1, annotation_id, resource_type="photometry"
        )
    assert err.value.status_code == 400

    sp.delete_annotation(photometry_id, annotation_id, resource_type="photometry")

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(photometry_id, annotation_id, resource_type="photometry")
    assert err.value.status_code == 403


def test_fetch_all_photometry_annotations(
    annotation_token, upload_data_token, public_source, public_group, ztf_camera
):
    photometry_id = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids="all",
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    sp = client(annotation_token)
    sp.post_annotation(
        photometry_id,
        "kowalski",
        {"gaia_G": 15.7},
        resource_type="photometry",
        group_ids=[public_group.id],
    )

    sp.post_annotation(
        photometry_id,
        "SEDM",
        {"redshift": 0.07},
        resource_type="photometry",
        group_ids=[public_group.id],
    )

    annotations = client(upload_data_token).fetch_annotations(
        photometry_id, resource_type="photometry"
    )

    # make sure the dictionaries are sorted
    annotations = sorted(annotations, key=lambda x: x.origin)

    assert len(annotations) == 2
    assert annotations[0].data["redshift"] == 0.07
    assert annotations[1].data["gaia_G"] == 15.7
