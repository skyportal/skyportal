import datetime

import pytest
from skyportal_py import SkyPortalError
from skyportal_py.spectra import SpectrumPost

from skyportal.tests import api, client


def test_add_and_retrieve_annotation_group_id(
    annotation_token, upload_data_token, public_source, public_group, lris
):
    spectrum_id = (
        client(upload_data_token)
        .post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
            )
        )
        .id
    )

    # try posting without an origin...
    # raw api: intentionally malformed payload the typed client can't produce (missing origin)
    status, data = api(
        "POST",
        f"spectra/{spectrum_id}/annotations",
        data={
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert status in [400]
    assert "origin: Field required" in data["message"]

    # this should not work, since "origin" is empty
    # raw api: intentionally malformed payload the typed client can't produce (empty origin)
    status, data = api(
        "POST",
        f"spectra/{spectrum_id}/annotations",
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
            spectrum_id,
            "kowalski",
            {"offset_from_host_galaxy": 1.5},
            resource_type="spectra",
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
            spectrum_id,
            "kowalski",
            {"offset_from_host_galaxy": 1.5},
            resource_type="spectra",
            group_ids=[public_group.id],
        )
    assert err.value.status_code in [500, 400]

    annotation = client(annotation_token).fetch_annotation(
        spectrum_id, annotation_id, resource_type="spectra"
    )
    assert annotation.data["offset_from_host_galaxy"] == 1.5


def test_add_and_retrieve_annotation_group_access(
    annotation_token_two_groups,
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
    lris,
):
    sp_two_groups = client(annotation_token_two_groups)
    sp = client(annotation_token)
    spectrum_id = (
        client(upload_data_token_two_groups)
        .post_spectrum(
            SpectrumPost(
                obj_id=str(public_source_two_groups.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids=[public_group2.id],
            )
        )
        .id
    )

    annotation_id = sp_two_groups.post_annotation(
        spectrum_id,
        "IPAC",
        {"distance_from_host": 7.4},
        resource_type="spectra",
        group_ids=[public_group2.id],
    ).annotation_id

    # This token belongs to public_group2
    annotation = sp_two_groups.fetch_annotation(
        spectrum_id, annotation_id, resource_type="spectra"
    )
    assert annotation.data["distance_from_host"] == 7.4

    # This token does not belong to public_group2
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(spectrum_id, annotation_id, resource_type="spectra")
    assert err.value.status_code == 403

    # Both tokens should be able to view this annotation, but not the underlying spectrum
    annotation_id = sp_two_groups.post_annotation(
        spectrum_id,
        "kowalski",
        {"ACAI_class": "type Ia"},
        resource_type="spectra",
        group_ids=[public_group.id, public_group2.id],
    ).annotation_id

    annotation = sp_two_groups.fetch_annotation(
        spectrum_id, annotation_id, resource_type="spectra"
    )
    assert annotation.data["ACAI_class"] == "type Ia"

    # the underlying spectrum is not accessible to group1
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(spectrum_id, annotation_id, resource_type="spectra")
    assert err.value.status_code == 403

    # post a new spectrum with an annotation, open to both groups
    spectrum_id = (
        client(upload_data_token_two_groups)
        .post_spectrum(
            SpectrumPost(
                obj_id=str(public_source_two_groups.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids=[public_group.id, public_group2.id],
            )
        )
        .id
    )

    annotation_id = sp_two_groups.post_annotation(
        spectrum_id,
        "kowalski",
        {"ACAI_class": "type Ia"},
        resource_type="spectra",
        group_ids=[public_group2.id],
    ).annotation_id

    # token for group1 can view the spectrum but cannot see the annotation
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(spectrum_id, annotation_id, resource_type="spectra")
    assert err.value.status_code == 403

    # Both tokens should be able to view annotation after updating group list
    sp_two_groups.update_annotation(
        spectrum_id,
        annotation_id,
        {"ACAI_class": "type IIn"},
        resource_type="spectra",
        group_ids=[public_group.id, public_group2.id],
    )

    # the new annotation on the new spectrum should now accessible
    annotation = sp.fetch_annotation(
        spectrum_id, annotation_id, resource_type="spectra"
    )
    assert annotation.data["ACAI_class"] == "type IIn"


def test_cannot_add_annotation_without_permission(
    view_only_token, upload_data_token, public_source, lris
):
    spectrum_id = (
        client(upload_data_token)
        .post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids="all",
            )
        )
        .id
    )

    # raw api: intentionally malformed request (singular "annotation" route) the typed client can't produce
    status, data = api(
        "POST",
        f"spectra/{spectrum_id}/annotation",
        data={"origin": "kowalski", "data": {"gaia_G": 14.5}},
        token=view_only_token,
    )
    assert status in [401, 405]
    assert data["status"] == "error"


def test_delete_annotation(annotation_token, upload_data_token, public_source, lris):
    sp = client(annotation_token)
    spectrum_id = (
        client(upload_data_token)
        .post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
                group_ids="all",
            )
        )
        .id
    )

    annotation_id = sp.post_annotation(
        spectrum_id, "kowalski", {"gaia_G": 14.5}, resource_type="spectra"
    ).annotation_id

    annotation = sp.fetch_annotation(
        spectrum_id, annotation_id, resource_type="spectra"
    )
    assert annotation.data["gaia_G"] == 14.5

    # try to delete using the wrong spectrum ID
    with pytest.raises(
        SkyPortalError,
        match="Annotation resource ID does not match resource ID given in path",
    ) as err:
        sp.delete_annotation(spectrum_id + 1, annotation_id, resource_type="spectra")
    assert err.value.status_code == 400

    sp.delete_annotation(spectrum_id, annotation_id, resource_type="spectra")

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_annotation(spectrum_id, annotation_id, resource_type="spectra")
    assert err.value.status_code == 403


def test_fetch_all_spectrum_annotations(
    annotation_token, upload_data_token, public_source, public_group, lris
):
    spectrum_id = (
        client(upload_data_token)
        .post_spectrum(
            SpectrumPost(
                obj_id=str(public_source.id),
                observed_at=str(datetime.datetime.now()),
                instrument_id=lris.id,
                wavelengths=[664, 665, 666],
                fluxes=[234.2, 232.1, 235.3],
            )
        )
        .id
    )

    sp = client(annotation_token)
    sp.post_annotation(
        spectrum_id,
        "kowalski",
        {"gaia_G": 15.7},
        resource_type="spectra",
        group_ids=[public_group.id],
    )

    sp.post_annotation(
        spectrum_id,
        "SEDM",
        {"redshift": 0.07},
        resource_type="spectra",
        group_ids=[public_group.id],
    )

    annotations = client(upload_data_token).fetch_annotations(
        spectrum_id, resource_type="spectra"
    )

    # make sure the dictionaries are sorted
    annotations = sorted(annotations, key=lambda x: x.origin)

    assert len(annotations) == 2
    assert annotations[0].data["redshift"] == 0.07
    assert annotations[1].data["gaia_G"] == 15.7
