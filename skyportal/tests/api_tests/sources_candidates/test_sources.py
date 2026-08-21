import uuid
from datetime import UTC, datetime, timedelta

import arrow
import astropy.units as u
import healpix_alchemy as ha
import numpy as np
import numpy.testing as npt
import pytest
from astropy.time import Time
from skyportal_py import SkyPortalError
from skyportal_py.classifications import ClassificationPost
from skyportal_py.followup_requests import FollowupRequestPost
from skyportal_py.groups import GroupPost
from skyportal_py.photometry import PhotometryPost
from skyportal_py.sources import (
    SourceGcnEventCrossmatchPost,
    SourceNotificationPost,
    SourcePost,
)
from skyportal_py.spectra import SpectrumPost
from skyportal_py.taxonomies import TaxonomyPost
from tdtax import __version__, taxonomy

from skyportal.models import cosmo
from skyportal.tests import api, client

from ....utils.naive_datetime import utcnow_naive


def test_source_list(view_only_token):
    client(view_only_token).fetch_sources()


def test_source_existence(view_only_token, public_source):
    sp = client(view_only_token)
    assert sp.source_exists(public_source.id)

    assert not sp.source_exists(public_source.id[:-1])


def test_token_user_retrieving_source(view_only_token, public_source):
    # raw api: raw-JSON shape assertion the typed model would mask
    status, data = api("GET", f"sources/{public_source.id}", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"] for k in ["ra", "dec", "redshift", "dm", "created_at", "id"]
    )
    assert "photometry" not in data["data"]


def test_token_user_retrieving_source_with_phot(view_only_token, public_source):
    # raw api: raw-JSON shape assertion the typed model would mask
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includePhotometry": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"]
        for k in ["ra", "dec", "redshift", "dm", "created_at", "id", "photometry"]
    )


def test_token_user_retrieving_source_with_phot_exists(view_only_token, public_source):
    source = client(view_only_token).fetch_source(
        public_source.id, include_photometry_exists=True
    )
    # the original asserted key presence; dm can legitimately be null
    assert source.photometry_exists is not None
    assert all(
        getattr(source, k) is not None for k in ["ra", "dec", "created_at", "id"]
    )


@pytest.mark.flaky(reruns=2)
def test_token_user_retrieving_source_with_thumbnails(view_only_token, public_source):
    # raw api: raw-JSON shape assertion the typed model would mask
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includeThumbnails": True},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(
        k in data["data"]
        for k in ["ra", "dec", "redshift", "dm", "created_at", "id", "thumbnails"]
    )


def test_token_user_retrieving_source_without_nested(
    view_only_token, public_group, upload_data_token
):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            group_ids=[public_group.id],
        )
    )

    page = client(view_only_token).fetch_sources(
        remove_nested=True, group_ids=[public_group.id]
    )
    assert len(page.sources) == 2
    assert all(
        getattr(page.sources[0], k) is not None
        for k in ["ra", "dec", "redshift", "created_at", "id"]
    )
    # removeNested strips these keys; the typed model defaults them to empty lists
    assert all(
        getattr(page.sources[0], k) == []
        for k in ["annotations", "groups", "thumbnails", "classifications"]
    )


def test_duplicate_sources(public_group, upload_data_token, ztf_camera):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 90.0 * np.random.random()
    sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=ra,
            dec=dec,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=ra + 0.0001,
            dec=dec + 0.0005,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id1,
            mjd=59801.4,
            instrument_id=ztf_camera.id,
            filter="ztfg",
            group_ids=[public_group.id],
            mag=12.4,
            magerr=0.3,
            limiting_mag=22,
            magsys="ab",
        )
    )
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id2,
            mjd=59801.3,
            instrument_id=ztf_camera.id,
            filter="ztfg",
            group_ids=[public_group.id],
            mag=12.4,
            magerr=0.3,
            limiting_mag=22,
            magsys="ab",
        )
    )

    source = sp.fetch_source(obj_id1)
    assert len(source.duplicates) == 1
    assert source.duplicates[0].ra == ra + 0.0001
    assert source.duplicates[0].dec == dec + 0.0005
    assert source.duplicates[0].obj_id == obj_id2
    assert np.isclose(source.duplicates[0].separation, 1.82, atol=0.05)

    source = sp.fetch_source(obj_id2)
    assert len(source.duplicates) == 1
    assert source.duplicates[0].ra == ra
    assert source.duplicates[0].dec == dec
    assert source.duplicates[0].obj_id == obj_id1
    assert np.isclose(source.duplicates[0].separation, 1.82, atol=0.05)


def test_token_user_update_source(super_admin_token, upload_data_token, public_source):
    client(super_admin_token).update_source(
        public_source.id,
        ra=234.22,
        dec=-22.33,
        redshift=3,
        transient=False,
        ra_dis=2.3,
    )

    source = client(upload_data_token).fetch_source(public_source.id)
    npt.assert_almost_equal(source.ra, 234.22)
    npt.assert_almost_equal(source.redshift, 3.0)
    npt.assert_almost_equal(
        cosmo.luminosity_distance(3.0).value, source.luminosity_distance
    )


def test_distance_modulus(super_admin_token, upload_data_token, public_source):
    client(super_admin_token).update_source(
        public_source.id,
        ra=234.22,
        dec=-22.33,
        altdata={"dm": 28.5},
        transient=False,
        ra_dis=2.3,
    )

    source = client(upload_data_token).fetch_source(public_source.id)
    npt.assert_almost_equal(10 ** ((28.5 / 5) - 5), source.luminosity_distance)
    npt.assert_almost_equal(28.5, source.dm)
    npt.assert_almost_equal(10 ** ((28.5 / 5) - 5), source.angular_diameter_distance)


def test_parallax(super_admin_token, upload_data_token, public_source):
    parallax = 0.001  # in arcsec = 1 kpc
    d_pc = 1 / parallax
    dm = 5.0 * np.log10(d_pc / (10.0))

    client(super_admin_token).update_source(
        public_source.id,
        ra=234.22,
        dec=-22.33,
        altdata={"parallax": parallax},
        transient=False,
        ra_dis=2.3,
    )

    source = client(upload_data_token).fetch_source(public_source.id)

    npt.assert_almost_equal(dm, source.dm)


def test_low_redshift(super_admin_token, upload_data_token, public_source):
    client(super_admin_token).update_source(
        public_source.id,
        ra=234.22,
        dec=-22.33,
        transient=False,
        ra_dis=2.3,
        redshift=0.00001,
    )

    source = client(upload_data_token).fetch_source(public_source.id)

    assert source.dm is None


def test_cannot_update_source_without_permission(view_only_token, public_source):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).update_source(
            public_source.id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
        )
    assert err.value.status_code == 401


def test_token_user_post_new_source(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    alias = str(uuid.uuid4())
    origin = str(uuid.uuid4())
    t0 = datetime.now(UTC)
    saved = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
            alias=[alias],
            origin=origin,
        )
    )
    assert saved.id == obj_id

    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id
    npt.assert_almost_equal(source.ra, 234.22)

    saved_at = source.groups[0].saved_at.replace(tzinfo=UTC)
    assert abs(saved_at - t0) < timedelta(seconds=60)

    assert alias == source.alias[0]
    assert origin == source.origin


def test_cannot_post_source_with_null_radec(
    upload_data_token, view_only_token, public_group
):
    obj_id = str(uuid.uuid4())
    # raw api: intentionally malformed payload (explicit null ra/dec) the typed client can't produce
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": None,
            "dec": None,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400


def test_add_source_without_group_id(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
        )
    )
    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id
    npt.assert_almost_equal(source.ra, 234.22)


def test_admin_save_source_as_other_user(
    upload_data_token,
    view_only_token,
    super_admin_token,
    view_only_user,
    super_admin_user,
    public_group,
):
    obj_id = str(uuid.uuid4())

    # we shouldn't be able to save as the super admin user using
    # the upload_data_token (which is not an admin token)
    source_data = SourcePost(
        id=obj_id,
        ra=234.22,
        dec=-22.33,
        group_ids=[public_group.id],
        saver_per_group_id={str(public_group.id): super_admin_user.id},
    )
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token).post_source(source_data)
    assert err.value.status_code == 400
    assert (
        str(err.value)
        == "Failed to post source: You must be an admin to specify a saver_per_group_id field."
    )

    # now save it to the public group as the view only user, using the super admin token
    source_data.saver_per_group_id = {str(public_group.id): view_only_user.id}
    saved = client(super_admin_token).post_source(source_data)
    assert saved.id == obj_id

    # check that the source was saved by the view only user successfully
    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id
    assert len(source.groups) > 0
    assert source.groups[0].saved_by.id == view_only_user.id


def test_source_notifications_unauthorized(
    source_notification_user_token, public_group, public_source
):
    with pytest.raises(SkyPortalError, match="Unauthorized") as err:
        client(source_notification_user_token).post_source_notification(
            SourceNotificationPost(
                group_ids=[public_group.id],
                source_id=public_source.id,
                level="hard",
                additional_notes="",
            )
        )
    assert err.value.status_code == 401


def test_token_user_source_summary(
    public_group, public_source, view_only_token_two_groups, public_group2
):
    now = utcnow_naive().isoformat()
    sp = client(view_only_token_two_groups)

    sources = sp.fetch_sources_save_summary(group_ids=[public_group.id]).sources

    assert len(sources) == 1
    source = sources[0]
    # save records carry no ra/dec; SavedSource forbids extra keys, so
    # validation would fail if the server returned them

    assert source.obj_id == public_source.id
    assert source.group_id == public_group.id

    sources = sp.fetch_sources_save_summary(
        saved_after=now, group_ids=[public_group.id]
    ).sources

    assert len(sources) == 0

    sources = sp.fetch_sources_save_summary(group_ids=[public_group2.id]).sources
    assert len(sources) == 0

    sources = sp.fetch_sources_save_summary(
        saved_before=now, group_ids=[public_group.id]
    ).sources

    assert len(sources) == 1
    source = sources[0]

    assert source.obj_id == public_source.id
    assert source.group_id == public_group.id

    # check the datetime formatting is properly validated
    with pytest.raises(SkyPortalError) as err:
        sp.fetch_sources_save_summary(
            saved_before="2020-104-01T00:00:01.2412", group_ids=[public_group.id]
        )
    assert err.value.status_code == 400


def test_source_summary_pagination(super_admin_user, super_admin_token):
    sp = client(super_admin_token)
    group_name = str(uuid.uuid4())
    new_group_id = sp.post_group(
        GroupPost(name=group_name, group_admins=[super_admin_user.id])
    ).id
    ids = set()
    for _ in range(1, 51):
        id = str(uuid.uuid4())
        ids.add(id)
        sp.post_source(
            SourcePost(
                id=id,
                ra=234.22,
                dec=22.33,
                group_ids=[new_group_id],
            )
        )

    sources = sp.fetch_sources_save_summary(group_ids=[new_group_id]).sources
    assert len(sources) == 50
    # save records carry no ra/dec; SavedSource forbids extra keys, so
    # validation would fail if the server returned them

    fetched_ids = set()
    for i in range(1, 6):
        sources = sp.fetch_sources_save_summary(
            group_ids=[new_group_id], page_number=i, num_per_page=10
        ).sources
        assert len(sources) == 10
        for source in sources:
            assert source.obj_id in ids
            fetched_ids.add(source.obj_id)

    assert len(fetched_ids) == 50


def test_sources_sorting(upload_data_token, view_only_token, public_group):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    ra1 = 230
    ra2 = 240

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(
            id=obj_id,
            ra=ra1,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
            altdata={"Einstein Radius": 0.2, "nested": {"key": 2}},
        )
    )
    assert saved.id == obj_id

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=ra2,
            dec=-22.33,
            redshift=3,
            transient=False,
            ra_dis=2.3,
            group_ids=[public_group.id],
            altdata={"Einstein Radius": 0.3, "nested": {"key": 1}},
        )
    )
    assert saved.id == obj_id2

    # Sort sources by ra, desc and check that source 2 is first
    page = client(view_only_token).fetch_sources(
        sort_by="ra", sort_order="desc", group_ids=[public_group.id]
    )
    assert page.sources[0].id == obj_id2
    npt.assert_almost_equal(page.sources[0].ra, ra2)
    assert page.sources[1].id == obj_id
    npt.assert_almost_equal(page.sources[1].ra, ra1)

    # next let's sort by the altdata.Einstein Radius descending
    page = client(view_only_token).fetch_sources(
        sort_by="altdata.Einstein Radius",
        sort_order="desc",
        group_ids=[public_group.id],
    )
    assert page.sources[0].id == obj_id2
    npt.assert_almost_equal(page.sources[0].altdata["Einstein Radius"], 0.3)
    assert page.sources[1].id == obj_id
    npt.assert_almost_equal(page.sources[1].altdata["Einstein Radius"], 0.2)

    # let's try the same but ascending, which should reverse the order
    page = client(view_only_token).fetch_sources(
        sort_by="altdata.Einstein Radius",
        sort_order="asc",
        group_ids=[public_group.id],
    )
    assert page.sources[0].id == obj_id
    npt.assert_almost_equal(page.sources[0].altdata["Einstein Radius"], 0.2)
    assert page.sources[1].id == obj_id2
    npt.assert_almost_equal(page.sources[1].altdata["Einstein Radius"], 0.3)

    # let's try sorting on an altdata nested field
    page = client(view_only_token).fetch_sources(
        sort_by="altdata.nested.key",
        sort_order="asc",
        group_ids=[public_group.id],
    )
    assert page.sources[0].id == obj_id2
    assert page.sources[1].id == obj_id

    # try it in descending order to validate
    page = client(view_only_token).fetch_sources(
        sort_by="altdata.nested.key",
        sort_order="desc",
        group_ids=[public_group.id],
    )
    assert page.sources[0].id == obj_id
    assert page.sources[1].id == obj_id2


def test_sources_sorting_by_annotation(
    upload_data_token, super_admin_token, public_group, annotation_token
):
    obj_id = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    origin = str(uuid.uuid4())
    key = "t_E"

    for oid, ra in [(obj_id, 210), (obj_id2, 220)]:
        client(upload_data_token).post_source(
            SourcePost(
                id=oid,
                ra=ra,
                dec=-22.33,
                group_ids=[public_group.id],
            )
        )

    # Values 9 and 10 are chosen so numeric and lexicographic order disagree.
    for oid, value in [(obj_id, 9), (obj_id2, 10)]:
        client(annotation_token).post_annotation(oid, origin, {key: value})

    # Descending: 10 (obj_id2) must come first; a text sort would rank "9" first.
    page = client(super_admin_token).fetch_sources(
        sort_by=f"annotation.{origin}.{key}",
        sort_order="desc",
        group_ids=[public_group.id],
    )
    assert page.sources[0].id == obj_id2
    assert page.sources[1].id == obj_id

    # Ascending reverses the order.
    page = client(super_admin_token).fetch_sources(
        sort_by=f"annotation.{origin}.{key}",
        sort_order="asc",
        group_ids=[public_group.id],
    )
    assert page.sources[0].id == obj_id
    assert page.sources[1].id == obj_id2


def test_sources_sorting_by_annotation_no_leakage(
    upload_data_token,
    annotation_token,
    annotation_token_two_groups,
    view_only_token,
    super_admin_token,
    public_group,
    public_group2,
):
    # Two sources both saved to public_group (so a public_group-only user sees
    # both). obj_visible has an annotation in public_group; obj_hidden's only
    # annotation is shared with public_group2, which that user cannot access.
    obj_visible = str(uuid.uuid4())
    obj_hidden = str(uuid.uuid4())
    origin = str(uuid.uuid4())
    key = "t_E"

    for oid, ra in [(obj_visible, 210), (obj_hidden, 220)]:
        client(upload_data_token).post_source(
            SourcePost(
                id=oid,
                ra=ra,
                dec=-22.33,
                group_ids=[public_group.id],
            )
        )

    # Accessible annotation (small value) on obj_visible.
    client(annotation_token).post_annotation(
        obj_visible, origin, {key: 5}, group_ids=[public_group.id]
    )

    # Larger-valued annotation on obj_hidden, shared only with public_group2.
    client(annotation_token_two_groups).post_annotation(
        obj_hidden, origin, {key: 100}, group_ids=[public_group2.id]
    )

    # A user who can access public_group2 (here the admin) sees the value 100
    # and sorts obj_hidden first when descending.
    page = client(super_admin_token).fetch_sources(
        sort_by=f"annotation.{origin}.{key}",
        sort_order="desc",
        group_ids=[public_group.id],
    )
    ids = [s.id for s in page.sources]
    assert ids[0] == obj_hidden
    assert ids[1] == obj_visible

    # A public_group-only user must NOT see the public_group2 annotation, so its
    # value cannot influence the sort: obj_hidden has no accessible annotation
    # and sorts last (NULLS LAST), while obj_visible (value 5) comes first. If
    # the hidden value leaked, obj_hidden (value 100) would sort first here.
    page = client(view_only_token).fetch_sources(
        sort_by=f"annotation.{origin}.{key}",
        sort_order="desc",
        group_ids=[public_group.id],
    )
    ids = [s.id for s in page.sources]
    assert obj_visible in ids and obj_hidden in ids
    assert ids[0] == obj_visible
    assert ids[-1] == obj_hidden


def test_object_last_detected(
    upload_data_token,
    view_only_token,
    public_source,
    ztf_camera,
    public_group,
    upload_data_token_two_groups,
    public_group2,
):
    # Some very high mjd to make this the latest point
    # This is not a detection though
    client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=99999.0,
            instrument_id=ztf_camera.id,
            mag=None,
            magerr=None,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    # Another high mjd, but this time a photometry point not visible to the user
    client(upload_data_token_two_groups).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=99900.0,
            instrument_id=ztf_camera.id,
            mag=None,
            magerr=None,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group2.id],
        )
    )

    # A high mjd, but lower than the first point
    # Since this is a detection, it should be returned as "last_detected"
    client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=90000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    source = client(view_only_token).fetch_source(
        public_source.id, include_detection_stats=True
    )
    assert arrow.get(
        Time(source.photstats[-1].last_detected_mjd, format="mjd").datetime
    ) == arrow.get((90000.0 - 40_587) * 86400.0)


def test_source_photometry_summary_info(
    upload_data_token, view_only_token, public_source_no_data, ztf_camera, public_group
):
    pt1 = {"mjd": 58001.0, "flux": 13.24}
    pt2 = {"mjd": 58002.0, "flux": 15.24}
    posted = client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=str(public_source_no_data.id),
            mjd=[pt1["mjd"], pt2["mjd"]],
            instrument_id=ztf_camera.id,
            flux=[pt1["flux"], pt2["flux"]],
            fluxerr=[0.031, 0.031],
            filter=["ztfg", "ztfg"],
            zp=[25.0, 25.0],
            magsys=["ab", "ab"],
            ra=264.1947917,
            dec=[50.5478333, 50.5478333],
            dec_unc=0.2,
            group_ids=[public_group.id],
        )
    )
    assert len(posted.ids) == 2

    mag1_ab = -2.5 * np.log10(pt1["flux"]) + 25.0
    mag2_ab = -2.5 * np.log10(pt2["flux"]) + 25.0

    source = client(view_only_token).fetch_source(
        public_source_no_data.id, include_detection_stats=True
    )

    assert source.photstats[-1].first_detected_mjd == pt1["mjd"]
    assert source.photstats[-1].first_detected_mag == mag1_ab
    assert source.photstats[-1].peak_mjd_global == pt2["mjd"]
    assert source.photstats[-1].peak_mag_global == mag2_ab


# Sources filtering tests
def test_sources_filter_by_name_or_id(upload_data_token, view_only_token, public_group):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(id=obj_id1, ra=230, dec=-22.33, group_ids=[public_group.id])
    )
    assert saved.id == obj_id1
    saved = sp.post_source(
        SourcePost(id=obj_id2, ra=230, dec=-22.33, group_ids=[public_group.id])
    )
    assert saved.id == obj_id2

    # Filter for obj 1 only, using a substring not matched in the other one
    page = client(view_only_token).fetch_sources(
        source_id=obj_id1[0:5], group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Filter for obj 1 only, rejecting object 2
    page = client(view_only_token).fetch_sources(
        rejected_source_ids=[obj_id2], group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Reject object 1 and 2
    page = client(view_only_token).fetch_sources(
        rejected_source_ids=[obj_id1, obj_id2], group_ids=[public_group.id]
    )
    assert len(page.sources) == 0


def test_sources_filter_by_position(upload_data_token, view_only_token, public_group):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(id=obj_id1, ra=230, dec=-22.33, group_ids=[public_group.id])
    )
    assert saved.id == obj_id1
    saved = sp.post_source(
        SourcePost(id=obj_id2, ra=500, dec=0, group_ids=[public_group.id])
    )
    assert saved.id == obj_id2

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        ra=229, dec=-22, radius=5, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1


def test_sources_filter_by_position_small_radius(
    upload_data_token, view_only_token, public_group
):
    # Two sources 3 arcsec apart in dec; exercises the healpix cone prefilter
    # at arcsec scale and its radius boundary.
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    ra, dec = 100.0, 20.0
    for oid, d in [(obj_id1, dec), (obj_id2, dec + 3 / 3600)]:
        client(upload_data_token).post_source(
            SourcePost(id=oid, ra=ra, dec=d, group_ids=[public_group.id])
        )

    # 2 arcsec radius: only obj 1 (obj 2 is 3 arcsec away, outside).
    page = client(view_only_token).fetch_sources(
        ra=ra, dec=dec, radius=2 / 3600, group_ids=[public_group.id]
    )
    assert {s.id for s in page.sources} == {obj_id1}

    # 4 arcsec radius: both sources are within.
    page = client(view_only_token).fetch_sources(
        ra=ra, dec=dec, radius=4 / 3600, group_ids=[public_group.id]
    )
    assert {s.id for s in page.sources} == {obj_id1, obj_id2}


def test_sources_filter_by_time_saved(upload_data_token, view_only_token, public_group):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1
    test_time = datetime.now(UTC)
    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        saved_before=test_time.isoformat(), group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        saved_after=test_time.isoformat(), group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2


def test_sources_filter_by_saved_by_current_user(
    upload_data_token, view_only_token2, public_group
):
    # upload_data_token and view_only_token2 are different users, both in
    # public_group; only the former saves the source below.
    obj_id = str(uuid.uuid4())

    saved = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id

    # The saver sees it when filtering to their own saves
    page = client(upload_data_token).fetch_sources(
        saved_by_current_user=True, group_ids=[public_group.id]
    )
    assert obj_id in [s.id for s in page.sources]

    # Another group member who did not save it does not see it
    page = client(view_only_token2).fetch_sources(
        saved_by_current_user=True, group_ids=[public_group.id]
    )
    assert obj_id not in [s.id for s in page.sources]


def test_sources_filter_by_time_spectrum(
    upload_data_token, view_only_token, public_group, lris
):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1
    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    # Add spectrum to source 1
    sp.post_spectrum(
        SpectrumPost(
            obj_id=obj_id1,
            observed_at=str(datetime.now(UTC) - timedelta(days=1)),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    )

    test_time = datetime.now(UTC)
    # Add spectrum to source 2
    sp.post_spectrum(
        SpectrumPost(
            obj_id=obj_id2,
            observed_at=str(datetime.now(UTC) + timedelta(days=1)),
            instrument_id=lris.id,
            wavelengths=[664, 665, 666],
            fluxes=[234.2, 232.1, 235.3],
            group_ids=[public_group.id],
        )
    )

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        has_spectrum_before=test_time.isoformat(), group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        has_spectrum_after=test_time.isoformat(), group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2


def test_sources_filter_by_last_detected(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    # Add a detection to obj 1
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id1,
            mjd=[59000.0],
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        start_date=arrow.get((58500 - 40_587) * 86400.0).isoformat(),
        group_ids=[public_group.id],
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    page = client(view_only_token).fetch_sources(
        end_date=arrow.get((59000 - 40_587) * 86400.0).isoformat(),
        group_ids=[public_group.id],
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1


def test_sources_filter_by_simbad_class(
    upload_data_token, view_only_token, public_group
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    simbad_class = str(uuid.uuid4())

    # Upload two new sources
    saved = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            altdata={"simbad": {"class": simbad_class}},
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    saved = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        simbad_class=simbad_class, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1


def test_sources_filter_by_classifications(
    upload_data_token,
    taxonomy_token,
    classification_token,
    view_only_token,
    public_group,
):
    # Post a source with a classification, and one without
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )

    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name=taxonomy_name,
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    client(classification_token).post_classification(
        ClassificationPost(
            obj_id=obj_id1,
            classification="Algol",
            taxonomy_id=taxonomy_id,
            probability=1.0,
            group_ids=[public_group.id],
        )
    )

    client(classification_token).post_classification(
        ClassificationPost(
            obj_id=obj_id2,
            classification="AGN",
            taxonomy_id=taxonomy_id,
            probability=1.0,
            group_ids=[public_group.id],
        )
    )

    # Filter for sources with classification "Algol" - should only get obj_id1 back
    page = client(view_only_token).fetch_sources(
        classifications=[f"{taxonomy_name}: Algol"], group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Filter for sources with nonclassification "Algol" - should at least get obj_id2 back
    page = client(view_only_token).fetch_sources(
        nonclassifications=[f"{taxonomy_name}: Algol"], group_ids=[public_group.id]
    )
    assert any(source.id == obj_id2 for source in page.sources)


def test_sources_filter_by_unclassified(
    upload_data_token,
    taxonomy_token,
    classification_token,
    view_only_token,
    public_group,
):
    # Post a source with a classification, and one without
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )

    taxonomy_name = "test taxonomy" + str(uuid.uuid4())
    taxonomy_id = (
        client(taxonomy_token)
        .post_taxonomy(
            TaxonomyPost(
                name=taxonomy_name,
                hierarchy=taxonomy,
                group_ids=[public_group.id],
                provenance=f"tdtax_{__version__}",
                version=__version__,
                is_latest=True,
            )
        )
        .taxonomy_id
    )

    classification_id = (
        client(classification_token)
        .post_classification(
            ClassificationPost(
                obj_id=obj_id,
                classification="Algol",
                taxonomy_id=taxonomy_id,
                probability=1.0,
                group_ids=[public_group.id],
            )
        )
        .classification_id
    )

    # Filter for all sources
    page = client(view_only_token).fetch_sources(
        unclassified=False, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id

    # Filter for unclassified sources
    page = client(view_only_token).fetch_sources(
        unclassified=True, group_ids=[public_group.id]
    )
    assert len(page.sources) == 0

    # now delete that classification
    client(classification_token).delete_classification(classification_id)

    # now filter for unclassified sources again
    page = client(view_only_token).fetch_sources(
        unclassified=True, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id


def test_sources_filter_by_redshift(upload_data_token, view_only_token, public_group):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            redshift=1,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        min_redshift=2, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        max_redshift=2, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2


def test_sources_filter_by_peak_mag(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources with differing large mags
    sp = client(upload_data_token)
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id1,
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=55,
            magerr=0.1,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id2,
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=50,
            magerr=0.1,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        min_peak_magnitude=51, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        max_peak_magnitude=51, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1


def test_sources_filter_by_latest_mag(
    upload_data_token, view_only_token, public_group, ztf_camera
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources with differing latest mags
    sp = client(upload_data_token)
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id1,
            mjd=59000.0,
            instrument_id=ztf_camera.id,
            mag=25,
            magerr=0.1,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id2,
            mjd=59000.0,
            instrument_id=ztf_camera.id,
            mag=22,
            magerr=0.1,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        max_latest_magnitude=23, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        min_latest_magnitude=23, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2


def test_sources_filter_by_has_tns_name(
    upload_data_token, view_only_token, public_group
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    # Upload two new sources
    sp = client(upload_data_token)
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
            tns_name="test_tns_name",
        )
    )
    assert saved.id == obj_id1

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    # Filter for obj 1 only
    page = client(view_only_token).fetch_sources(
        has_tns_name=True, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id1

    # An explicit "false" must not enable the filter (it used to be truthy)
    page = client(view_only_token).fetch_sources(
        has_tns_name=False, group_ids=[public_group.id]
    )
    returned_ids = {s.id for s in page.sources}
    assert {obj_id1, obj_id2}.issubset(returned_ids)


def test_sources_filter_by_has_spectrum(
    view_only_token,
    public_group,
    public_source,
    public_source_no_data,
):
    # Filter for obj 1 only, since the no data source will not have spectra
    page = client(view_only_token).fetch_sources(
        has_spectrum=True, group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == public_source.id


def test_sources_hidden_photometry_not_leaked(
    public_source,
    ztf_camera,
    public_group,
    public_group2,
    view_only_token,
    upload_data_token_two_groups,
):
    obj_id = str(public_source.id)
    # Post photometry to the object belonging to a different group
    photometry_id = (
        client(upload_data_token_two_groups)
        .post_photometry(
            PhotometryPost(
                obj_id=obj_id,
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

    # Check for single GET call as well
    source = client(view_only_token).fetch_source(obj_id, include_photometry=True)
    assert source.id == obj_id
    assert len(public_source.photometry) - 1 == len(source.photometry)
    assert photometry_id not in (x.id for x in source.photometry)


def test_source_healpix(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=229.9620403,
            dec=34.8442757,
            redshift=3,
            group_ids=[public_group.id],
        )
    )

    source = client(view_only_token).fetch_source(obj_id)
    healpix = ha.constants.HPX.lonlat_to_healpix(
        229.9620403 * u.deg, 34.8442757 * u.deg
    )
    assert source.healpix == healpix


def test_filter_sources_by_created_at(
    super_admin_token, upload_data_token, view_only_token, public_group
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    time_before_both = datetime.now(UTC)

    # Upload two new sources
    sp = client(upload_data_token)
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    partition_time = datetime.now(UTC)

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    time_after_both = datetime.now(UTC)

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        created_or_modified_after=str(partition_time), group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2

    # Fetch both
    page = client(view_only_token).fetch_sources(
        created_or_modified_after=str(time_before_both), group_ids=[public_group.id]
    )
    assert len(page.sources) == 2

    # Filter both out
    page = client(view_only_token).fetch_sources(
        created_or_modified_after=str(time_after_both), group_ids=[public_group.id]
    )
    assert len(page.sources) == 0


def test_filter_sources_by_modified(
    super_admin_token, upload_data_token, view_only_token, public_group
):
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())

    time_before_both = datetime.now(UTC)

    # Upload two new sources
    sp = client(upload_data_token)
    saved = sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id1

    saved = sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert saved.id == obj_id2

    partition_time = datetime.now(UTC)

    client(super_admin_token).update_source(obj_id2, ra=234.11, dec=-22.11)

    time_after_both = datetime.now(UTC)

    # Filter for obj 2 only
    page = client(view_only_token).fetch_sources(
        created_or_modified_after=str(partition_time), group_ids=[public_group.id]
    )
    assert len(page.sources) == 1
    assert page.sources[0].id == obj_id2

    # Fetch both
    page = client(view_only_token).fetch_sources(
        created_or_modified_after=str(time_before_both), group_ids=[public_group.id]
    )
    assert len(page.sources) == 2

    # Filter both out
    page = client(view_only_token).fetch_sources(
        created_or_modified_after=str(time_after_both), group_ids=[public_group.id]
    )
    assert len(page.sources) == 0


def test_token_user_retrieving_source_with_period_exists(
    view_only_token, public_source, annotation_token
):
    client(annotation_token).post_annotation(
        public_source.id, "kowalski", {"period": 1.5}
    )

    source = client(view_only_token).fetch_source(
        public_source.id, include_period_exists=True
    )
    assert source.period_exists


def test_token_user_retrieving_source_with_annotation_filter(
    super_admin_token, public_source, public_source_two_groups, annotation_token
):
    annotation_name_1 = str(uuid.uuid4())
    annotation_name_2 = str(uuid.uuid4())

    client(annotation_token).post_annotation(
        public_source.id,
        "kowalski",
        {annotation_name_1: 1.5, annotation_name_2: 0.0},
    )

    client(annotation_token).post_annotation(
        public_source_two_groups.id,
        "gloria",
        {annotation_name_1: 1.5, annotation_name_2: 1.0},
    )

    sp = client(super_admin_token)
    page = sp.fetch_sources(
        annotations_filter=f"{annotation_name_1}",
        sort_by="saved_at",
        sort_order="desc",
    )
    assert len(page.sources) == 2

    page = sp.fetch_sources(
        annotations_filter=f"{annotation_name_1}:2.0:le",
        sort_by="saved_at",
        sort_order="desc",
    )
    assert len(page.sources) == 2

    page = sp.fetch_sources(
        annotations_filter=f"{annotation_name_1}:2.0:le",
        annotations_filter_origin="kowalski",
        sort_by="saved_at",
        sort_order="desc",
    )
    assert len(page.sources) == 1

    page = sp.fetch_sources(
        annotations_filter=f"{annotation_name_1}:2.0:ge",
        sort_by="saved_at",
        sort_order="desc",
    )
    assert len(page.sources) == 0

    page = sp.fetch_sources(
        annotations_filter=f"{annotation_name_1}:2.0:le,{annotation_name_2}:0.5:le",
        sort_by="saved_at",
        sort_order="desc",
    )
    assert len(page.sources) == 1


def test_add_source_redshift_origin(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            redshift_origin="host-spectrum",
            transient=False,
            ra_dis=2.3,
        )
    )
    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id

    assert np.isclose(source.redshift, 3)
    assert source.redshift_origin == "host-spectrum"


def test_token_user_retrieving_source_with_comment_filter(
    super_admin_token, public_source, public_source_two_groups, comment_token
):
    comment_text = str(uuid.uuid4())
    comment_text_less = comment_text[:-4]

    client(comment_token).post_comment(public_source.id, comment_text)

    client(comment_token).post_comment(public_source_two_groups.id, comment_text_less)

    page = client(super_admin_token).fetch_sources(
        comments_filter=f"{comment_text_less}",
        sort_by="saved_at",
        sort_order="desc",
    )
    # we support partial matches now, so we should get 2 sources here
    assert len(page.sources) == 2

    page = client(super_admin_token).fetch_sources(
        comments_filter=f"{comment_text}",
        sort_by="saved_at",
        sort_order="desc",
    )
    # but only one source here with the full comment
    assert len(page.sources) == 1


def test_patch_healpix(
    super_admin_token, upload_data_token, view_only_token, public_group
):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            redshift=3,
            group_ids=[public_group.id],
            ra=234.22,
            dec=-22.33,
        )
    )

    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id
    assert source.healpix == 3120579787410559663

    client(super_admin_token).update_source(
        obj_id,
        ra=230.22,
        dec=-22.33,
        transient=False,
        ra_dis=2.3,
        redshift=0.00001,
    )

    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id
    assert source.healpix == 3126137476541327364


def test_filter_followup_request(
    upload_data_token, view_only_token, public_group, public_group_sedm_allocation
):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
        )
    )
    source = client(view_only_token).fetch_source(obj_id)
    assert source.id == obj_id

    client(upload_data_token).post_followup_request(
        FollowupRequestPost(
            allocation_id=public_group_sedm_allocation.id,
            obj_id=obj_id,
            payload={
                "priority": 5,
                "start_date": "3010-09-01",
                "end_date": "3012-09-01",
                "observation_type": "IFU",
                "exposure_time": 300,
                "maximum_airmass": 2,
                "maximum_fwhm": 1.2,
            },
        )
    )

    page = client(view_only_token).fetch_sources(has_followup_request=True)
    assert any(obj.id == obj_id for obj in page.sources)


def test_add_and_delete_source_label(upload_data_token, view_only_token, public_group):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
        )
    )

    source = client(view_only_token).fetch_source(obj_id, include_labellers=True)
    assert source.id == obj_id

    assert len(source.labellers) == 0

    client(upload_data_token).post_source_labels(obj_id, [public_group.id])

    source = client(view_only_token).fetch_source(obj_id, include_labellers=True)
    assert source.id == obj_id

    assert len(source.labellers) == 1

    client(upload_data_token).delete_source_labels(obj_id, [public_group.id])

    source = client(view_only_token).fetch_source(obj_id, include_labellers=True)
    assert source.id == obj_id

    assert len(source.labellers) == 0


def test_copy_photometry_sources(
    public_group, upload_data_token, ztf_camera, view_only_token
):
    sp = client(upload_data_token)
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 89.0 * np.random.random()
    sp.post_source(
        SourcePost(
            id=obj_id1,
            ra=ra,
            dec=dec,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    sp.post_source(
        SourcePost(
            id=obj_id2,
            ra=ra + 0.0001,
            dec=dec + 0.0005,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id1,
            mjd=59801.4,
            instrument_id=ztf_camera.id,
            filter="ztfg",
            group_ids=[public_group.id],
            mag=12.4,
            magerr=0.3,
            limiting_mag=22,
            magsys="ab",
        )
    )
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id2,
            mjd=59801.3,
            instrument_id=ztf_camera.id,
            filter="ztfg",
            group_ids=[public_group.id],
            mag=12.4,
            magerr=0.3,
            limiting_mag=22,
            magsys="ab",
        )
    )

    sp.post_source_photometry_copy(obj_id1, obj_id2, [public_group.id])

    source = client(view_only_token).fetch_source(obj_id1, include_photometry=True)
    assert any(np.isclose(p.mjd, 59801.3) for p in source.photometry)


def test_deduplicate_photometry(
    public_group, upload_data_token, ztf_camera, view_only_token
):
    sp = client(upload_data_token)
    obj_id = str(uuid.uuid4())
    ra = 200.0 * np.random.random()
    dec = 89.0 * np.random.random()
    sp.post_source(
        SourcePost(
            id=obj_id,
            ra=ra,
            dec=dec,
            redshift=3,
            group_ids=[public_group.id],
        )
    )
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id,
            mjd=59801.4,
            instrument_id=ztf_camera.id,
            filter="ztfg",
            group_ids=[public_group.id],
            mag=12.4,
            magerr=0.3,
            limiting_mag=22,
            magsys="ab",
        )
    )
    sp.post_photometry(
        PhotometryPost(
            obj_id=obj_id,
            mjd=59801.4,
            instrument_id=ztf_camera.id,
            filter="ztfg",
            group_ids=[public_group.id],
            mag=12.8,
            magerr=0.3,
            limiting_mag=22,
            magsys="ab",
        )
    )

    source = client(view_only_token).fetch_source(obj_id, include_photometry=True)
    assert len(source.photometry) == 2

    source = client(view_only_token).fetch_source(
        obj_id, include_photometry=True, deduplicate_photometry=True
    )
    assert len(source.photometry) == 1
    # should be the second one (which is first in the list)
    assert np.isclose(source.photometry[0].mag, 12.8)


def test_source_gcn_crossmatch_event_filters(upload_data_token, public_source):
    sp = client(upload_data_token)
    # The crossmatch endpoint accepts GCN/localization tag+property cuts. A
    # malformed property filter is rejected synchronously (before the async
    # crossmatch), via the shared apply_gcn_event_filters helper.
    with pytest.raises(SkyPortalError, match="gcnPropertiesFilter") as err:
        sp.post_source_gcn_event_crossmatch(
            public_source.id,
            SourceGcnEventCrossmatchPost(
                start_date="2019-08-13T08:18:05",
                end_date="2019-08-19T08:18:05",
                gcn_properties_filter=["BNS:0.5"],  # 2 parts -> invalid (needs 1 or 3)
            ),
        )
    assert err.value.status_code == 400

    # Well-formed tag/property cuts are accepted (no matching events in range is
    # reported separately, so just confirm the filter params parse and apply).
    # No GCN events exist in that window in this test, so the endpoint reports
    # that rather than a filter error.
    with pytest.raises(SkyPortalError, match="Cannot find GcnEvents") as err:
        sp.post_source_gcn_event_crossmatch(
            public_source.id,
            SourceGcnEventCrossmatchPost(
                start_date="2019-08-13T08:18:05",
                end_date="2019-08-19T08:18:05",
                gcn_tag_keep=["GW"],
                gcn_properties_filter=["FAR:1.0:lt"],
            ),
        )
    assert err.value.status_code == 400


def test_source_gcn_crossmatch_returns_associated_events(
    super_admin_token, super_admin_user, public_source
):
    # includeGCNCrossmatches reports every event an obj is associated with,
    # rejections included: the source page hangs its keep/reject control off
    # this list, so hiding a rejection would leave no way to revisit it.
    import sqlalchemy as sa

    from skyportal.models import DBSession, GcnEvent, GcnEventObj

    dateobs = datetime(2019, 4, 25, 8, 18, 5)
    rejected_dateobs = datetime(2019, 4, 26, 8, 18, 5)

    session = DBSession()
    for d in (dateobs, rejected_dateobs):
        session.add(GcnEvent(dateobs=d, sent_by_id=super_admin_user.id))
    session.add(
        GcnEventObj(
            obj_id=public_source.id,
            dateobs=dateobs,
            status="confirmed",
            confirmer_id=super_admin_user.id,
        )
    )
    session.add(
        GcnEventObj(
            obj_id=public_source.id,
            dateobs=rejected_dateobs,
            status="rejected",
            confirmer_id=super_admin_user.id,
        )
    )
    session.commit()

    try:
        source = client(super_admin_token).fetch_source(
            public_source.id, include_gcn_crossmatches=True
        )
        crossmatches = source.gcn_crossmatch
        found = {arrow.get(c["dateobs"]).naive for c in crossmatches}
        assert dateobs in found, crossmatches
        assert rejected_dateobs in found, (
            "a rejected association vanished, leaving no way to undo it"
        )
    finally:
        session = DBSession()
        for row in session.scalars(
            sa.select(GcnEventObj).where(GcnEventObj.obj_id == public_source.id)
        ).all():
            session.delete(row)
        for d in (dateobs, rejected_dateobs):
            event = session.scalar(sa.select(GcnEvent).where(GcnEvent.dateobs == d))
            if event is not None:
                session.delete(event)
        session.commit()
