import asyncio
import os
import uuid

import numpy as np
import pandas as pd
import pytest
import sncosmo
import sqlalchemy as sa
from marshmallow.exceptions import ValidationError as MMValidationError
from skyportal_py import SkyPortalError
from skyportal_py.instruments import InstrumentPost
from skyportal_py.photometry import PhotometryPost, PhotometryUpdate
from skyportal_py.sources import SourcePost
from skyportal_py.telescopes import TelescopePost

from baselayer.app import models as baselayer_models
from baselayer.app.env import load_env
from skyportal.handlers.api.photometry import (
    add_external_photometry,
    bulk_upsert_photometry,
)
from skyportal.models import DBSession, Token, User
from skyportal.models.photometry import Photometry
from skyportal.tests import api, client

from ....utils.naive_datetime import utcnow_naive

_, cfg = load_env()
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


def test_token_user_post_get_photometry_data(
    upload_data_token, public_source, public_group, ztf_camera
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
            altdata={"some_key": "some_value"},
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")

    assert phot.ra is None
    assert phot.dec is None
    assert phot.ra_unc is None
    assert phot.dec_unc is None
    assert phot.altdata == {"some_key": "some_value"}

    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25.0 - 23.9)))


def test_ref_flux(upload_data_token, public_source, public_group, ztf_camera):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58003.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            ref_flux=8.01,
            ref_fluxerr=0.01,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
            altdata={"some_key": "some_value"},
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="both")

    assert phot.ra is None
    assert phot.dec is None
    assert phot.ra_unc is None
    assert phot.dec_unc is None
    assert phot.altdata == {"some_key": "some_value"}

    # correct for the difference in zeropoints
    corrected_flux = 12.24 / 10 ** (0.4 * (25.0 - 23.9))
    corrected_fluxerr = 0.031 / 10 ** (0.4 * (25.0 - 23.9))
    assert np.isclose(phot.flux, corrected_flux)
    assert phot.fluxerr == corrected_fluxerr
    assert phot.ref_flux == 8.01
    assert phot.ref_fluxerr == 0.01
    assert phot.tot_flux == 8.01 + corrected_flux
    assert phot.tot_fluxerr == np.sqrt(corrected_fluxerr**2 + 0.01**2)

    # what about magnitudes?
    assert np.isclose(phot.mag, -2.5 * np.log10(corrected_flux) + 23.9)
    assert np.isclose(
        phot.magerr, 2.5 / np.log(10) * corrected_fluxerr / corrected_flux
    )
    assert np.isclose(phot.magref, -2.5 * np.log10(8.01) + 23.9)
    assert np.isclose(phot.e_magref, 2.5 / np.log(10) * 0.01 / 8.01)
    assert np.isclose(phot.magtot, -2.5 * np.log10(8.01 + corrected_flux) + 23.9)
    total_mag_error_expected = (
        2.5
        / np.log(10)
        * np.sqrt(corrected_fluxerr**2 + 0.01**2)
        / (8.01 + corrected_flux)
    )
    assert np.isclose(phot.e_magtot, total_mag_error_expected)

    sp.delete_photometry(photometry_id)

    # give the reference flux a different zeropoint
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58003.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            ref_flux=8.01,
            ref_fluxerr=0.01,
            ref_zp=26.0,  # different zeropoint
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
            altdata={"some_key": "some_value"},
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="both")

    corrected_ref_flux = 8.01 / 10 ** (0.4 * (26.0 - 23.9))
    corrected_ref_fluxerr = 0.01 / 10 ** (0.4 * (26.0 - 23.9))

    assert np.isclose(phot.ref_flux, corrected_ref_flux)
    assert np.isclose(phot.ref_fluxerr, corrected_ref_fluxerr)
    assert np.isclose(phot.tot_flux, corrected_ref_flux + corrected_flux)
    assert np.isclose(
        phot.tot_fluxerr,
        np.sqrt(corrected_fluxerr**2 + corrected_ref_fluxerr**2),
    )

    # patch the reference flux
    sp.update_photometry(
        photometry_id,
        PhotometryUpdate(
            obj_id=str(public_source.id),
            mjd=58003.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
            ref_flux=9.02,
            ref_fluxerr=0.03,
            ref_zp=27.0,  # same zeropoint
        ),
    )
    phot = sp.fetch_photometry_point(photometry_id, format="both")
    corrected_ref_flux = 9.02 / 10 ** (0.4 * (27.0 - 23.9))
    corrected_ref_fluxerr = 0.03 / 10 ** (0.4 * (27.0 - 23.9))

    assert np.isclose(phot.ref_flux, corrected_ref_flux)
    assert np.isclose(phot.ref_fluxerr, corrected_ref_fluxerr)
    assert np.isclose(phot.tot_flux, corrected_ref_flux + corrected_flux)
    assert np.isclose(
        phot.tot_fluxerr,
        np.sqrt(corrected_fluxerr**2 + corrected_ref_fluxerr**2),
    )


def test_ref_mag(upload_data_token, public_source, public_group, ztf_camera):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58003.0,
            instrument_id=ztf_camera.id,
            mag=19.24,
            limiting_mag=20.5,
            magerr=0.123,
            magref=17.01,
            e_magref=0.01,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
            altdata={"some_key": "some_value"},
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="both")

    assert phot.altdata == {"some_key": "some_value"}

    expected_flux = 10 ** (-0.4 * (19.24 - 23.9))
    expected_fluxerr = 0.123 * (np.log(10) / 2.5) * expected_flux
    assert np.isclose(phot.flux, expected_flux)
    assert np.isclose(phot.fluxerr, expected_fluxerr)
    assert np.isclose(phot.mag, 19.24)
    assert np.isclose(phot.magerr, 0.123)
    assert np.isclose(phot.magref, 17.01)
    assert np.isclose(phot.e_magref, 0.01)

    expected_ref_flux = 10 ** (-0.4 * (17.01 - 23.9))
    expected_ref_fluxerr = 0.01 * (np.log(10) / 2.5) * expected_ref_flux
    assert np.isclose(phot.ref_flux, expected_ref_flux)
    assert np.isclose(phot.ref_fluxerr, expected_ref_fluxerr)
    assert np.isclose(phot.tot_flux, expected_ref_flux + expected_flux)
    assert np.isclose(
        phot.tot_fluxerr,
        np.sqrt(expected_fluxerr**2 + expected_ref_fluxerr**2),
    )

    assert np.isclose(
        phot.magtot,
        -2.5 * np.log10(expected_ref_flux + expected_flux) + 23.9,
    )

    expected_mag_error = 2.5 / np.log(10) * phot.tot_fluxerr / phot.tot_flux
    assert np.isclose(phot.e_magtot, expected_mag_error)

    # patch the reference mag
    sp.update_photometry(
        photometry_id,
        PhotometryUpdate(
            obj_id=str(public_source.id),
            mjd=58003.0,
            instrument_id=ztf_camera.id,
            mag=19.24,
            limiting_mag=20.5,
            magerr=0.123,
            magref=18.01,
            e_magref=0.02,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
            altdata={"some_key": "some_value"},
        ),
    )
    phot = sp.fetch_photometry_point(photometry_id, format="both")

    expected_ref_flux = 10 ** (-0.4 * (18.01 - 23.9))
    expected_ref_fluxerr = 0.02 * (np.log(10) / 2.5) * expected_ref_flux
    assert np.isclose(phot.ref_flux, expected_ref_flux)
    assert np.isclose(phot.ref_fluxerr, expected_ref_fluxerr)
    assert np.isclose(phot.tot_flux, expected_ref_flux + expected_flux)
    assert np.isclose(
        phot.tot_fluxerr,
        np.sqrt(expected_fluxerr**2 + expected_ref_fluxerr**2),
    )
    assert np.isclose(phot.magref, 18.01)
    assert np.isclose(phot.e_magref, 0.02)


def test_query_magnitudes(upload_data_token, public_source, public_group, ztf_camera):
    origin = str(uuid.uuid4())
    sp = client(upload_data_token)
    ids = sp.post_photometry(
        PhotometryPost(
            obj_id=public_source.id,
            instrument_id=ztf_camera.id,
            mjd=[59410, 59411, 59412],
            mag=[19.2, 19.3, np.random.uniform(19.3, 20)],
            magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
            magref=[18.1, 18.2, np.random.uniform(18.2, 19)],
            e_magref=[0.01, 0.02, np.random.uniform(0.01, 0.1)],
            limiting_mag=[20.0, 20.1, 20.2],
            magsys=["ab", "ab", "ab"],
            filter=["ztfr", "ztfg", "ztfr"],
            ra=[42.01, 42.01, 42.02],
            dec=[42.02, 42.01, 42.03],
            origin=origin,
            group_ids=[public_group.id],
            altdata={"key1": "value1"},
        )
    ).ids
    assert len(ids) == 3

    # check the first point is correct
    phot = sp.fetch_photometry_point(ids[0], format="flux")
    assert phot.magref == 18.1
    assert phot.e_magref == 0.01
    flux_trans1 = 10 ** (-0.4 * (19.2 - 23.9))
    fluxerr_trans1 = 0.05 / 2.5 * np.log(10) * flux_trans1
    assert np.isclose(phot.flux, flux_trans1)
    assert np.isclose(phot.fluxerr, fluxerr_trans1)
    flux_ref1 = 10 ** (-0.4 * (18.1 - 23.9))
    fluxerr_ref1 = 0.01 / 2.5 * np.log(10) * flux_ref1
    assert np.isclose(phot.ref_flux, flux_ref1)
    assert np.isclose(phot.ref_fluxerr, fluxerr_ref1)

    assert np.isclose(phot.tot_flux, flux_trans1 + flux_ref1)
    assert np.isclose(
        phot.tot_fluxerr,
        np.sqrt(fluxerr_trans1**2 + fluxerr_ref1**2),
    )

    # check the second point is correct
    phot = sp.fetch_photometry_point(ids[1], format="flux")
    assert phot.magref == 18.2
    assert phot.e_magref == 0.02

    flux_ref2 = 10 ** (-0.4 * (18.2 - 23.9))
    fluxerr_ref2 = 0.02 / 2.5 * np.log(10) * flux_ref2
    assert np.isclose(phot.ref_flux, flux_ref2)
    assert np.isclose(phot.ref_fluxerr, fluxerr_ref2)

    # see if we can filter points by ref flux
    mag_midpoint = (19.3 + 19.2) / 2
    flux_midpoint = 10 ** (-0.4 * (mag_midpoint - 23.9))
    ref_flux_midpoint = (flux_ref1 + flux_ref2) / 2
    ref_mag_midpoint = -2.5 * np.log10(ref_flux_midpoint) + 23.9
    tot_flux_midpoint = flux_midpoint + ref_flux_midpoint
    tot_mag_midpoint = -2.5 * np.log10(tot_flux_midpoint) + 23.9

    def get_photometry_points(*query_params):
        return (
            DBSession()
            .scalars(
                sa.select(Photometry).where(Photometry.origin == origin, *query_params)
            )
            .all()
        )

    phot = get_photometry_points()
    assert len(phot) == 3

    # now look only for those with mag above midpoint
    phot = get_photometry_points(Photometry.mag > mag_midpoint)
    assert len(phot) == 2
    phot = get_photometry_points(Photometry.mag < mag_midpoint)
    assert len(phot) == 1

    # now look only for those with ref mag above midpoint
    phot = get_photometry_points(Photometry.magref > ref_mag_midpoint)
    assert len(phot) == 2
    phot = get_photometry_points(Photometry.magref < ref_mag_midpoint)
    assert len(phot) == 1

    # now look only for those with tot mag above midpoint
    phot = get_photometry_points(Photometry.magtot > tot_mag_midpoint)
    assert len(phot) == 2
    phot = get_photometry_points(Photometry.magtot < tot_mag_midpoint)
    assert len(phot) == 1

    # check for fluxes above/below midpoint
    phot = get_photometry_points(Photometry.flux > flux_midpoint)
    assert len(phot) == 1
    phot = get_photometry_points(Photometry.flux < flux_midpoint)
    assert len(phot) == 2

    # check for ref fluxes above/below midpoint
    phot = get_photometry_points(Photometry.ref_flux > ref_flux_midpoint)
    assert len(phot) == 1
    phot = get_photometry_points(Photometry.ref_flux < ref_flux_midpoint)
    assert len(phot) == 2

    # check for tot fluxes above/below midpoint
    phot = get_photometry_points(Photometry.tot_flux > tot_flux_midpoint)
    assert len(phot) == 1
    phot = get_photometry_points(Photometry.tot_flux < tot_flux_midpoint)
    assert len(phot) == 2


def test_ref_mag_vector(upload_data_token, public_source, public_group, ztf_camera):
    ids = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                instrument_id=ztf_camera.id,
                mjd=[59410, 59411, 59412],
                mag=[19.2, 19.3, np.random.uniform(19, 20)],
                magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
                limiting_mag=[20.0, 20.1, 20.2],
                magsys=["ab", "ab", "ab"],
                filter=["ztfr", "ztfg", "ztfr"],
                ra=[42.01, 42.01, 42.02],
                dec=[42.02, 42.01, 42.03],
                origin=[None, "lol", "lol"],
                group_ids=[public_group.id],
                altdata={"key1": "value1"},
            )
        )
        .ids
    )
    assert len(ids) == 3

    for id in ids:
        phot = client(upload_data_token).fetch_photometry_point(id, format="flux")
        assert phot.altdata == {"key1": "value1"}


def test_post_multiple_photometry_vector_altdata(
    upload_data_token, public_source, public_group, ztf_camera
):
    ids = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                instrument_id=ztf_camera.id,
                mjd=[59408, 59409, 59410],
                mag=[19.2, 19.3, np.random.uniform(19, 20)],
                magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
                limiting_mag=[20.0, 20.1, 20.2],
                magsys=["ab", "ab", "ab"],
                filter=["ztfr", "ztfg", "ztfr"],
                ra=[42.01, 42.01, 42.02],
                dec=[42.02, 42.01, 42.03],
                origin=[None, "lol", "lol"],
                group_ids=[public_group.id],
                altdata=[{"key1": "value1"}, {"key2": "value2"}, {"key3": "value3"}],
            )
        )
        .ids
    )
    assert len(ids) == 3

    keys = []
    values = []
    for id in ids:
        phot = client(upload_data_token).fetch_photometry_point(id, format="flux")
        assert phot.altdata in [
            {"key1": "value1"},
            {"key2": "value2"},
            {"key3": "value3"},
        ]
        keys.append(list(phot.altdata.keys())[0])
        values.append(list(phot.altdata.values())[0])
    # Ensure each phot record was assigned associated distinct aldata value
    assert sorted(keys) == ["key1", "key2", "key3"]
    assert sorted(values) == ["value1", "value2", "value3"]


def test_post_multiple_photometry_scalar_altdata(
    upload_data_token, public_source, public_group, ztf_camera
):
    ids = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                instrument_id=ztf_camera.id,
                mjd=[59410, 59411, 59412],
                mag=[19.2, 19.3, np.random.uniform(19, 20)],
                magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
                limiting_mag=[20.0, 20.1, 20.2],
                magsys=["ab", "ab", "ab"],
                filter=["ztfr", "ztfg", "ztfr"],
                ra=[42.01, 42.01, 42.02],
                dec=[42.02, 42.01, 42.03],
                origin=[None, "lol", "lol"],
                group_ids=[public_group.id],
                altdata={"key1": "value1"},
            )
        )
        .ids
    )
    assert len(ids) == 3

    for id in ids:
        phot = client(upload_data_token).fetch_photometry_point(id, format="flux")
        assert phot.altdata == {"key1": "value1"}


def test_token_user_post_put_photometry_data(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    sp = client(upload_data_token)
    ids = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            instrument_id=ztf_camera.id,
            mjd=[59400, 59401, 59402],
            mag=[19.2, 19.3, np.random.uniform(19, 20)],
            magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
            limiting_mag=[20.0, 20.1, 20.2],
            magsys=["ab", "ab", "ab"],
            filter=["ztfr", "ztfg", "ztfr"],
            ra=[42.01, 42.01, 42.02],
            dec=[42.02, 42.01, 42.03],
            origin=[None, "lol", "lol"],
            group_ids=[public_group.id],
        )
    ).ids
    assert len(ids) == 3

    # POSTing photometry that contains the same first two points should fail:
    with pytest.raises(SkyPortalError) as err:
        sp.post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                instrument_id=ztf_camera.id,
                mjd=[59400, 59401, 59402],
                mag=[19.2, 19.3, np.random.uniform(19, 20)],
                magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
                limiting_mag=[20.0, 20.1, 20.2],
                magsys=["ab", "ab", "ab"],
                filter=["ztfr", "ztfg", "ztfr"],
                ra=[42.01, 42.01, 42.02],
                dec=[42.02, 42.01, 42.03],
                origin=[None, "lol", "lol"],
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400

    # PUTing photometry that contains
    # the same first point, the second point with a different origin, and a new third point should succeed
    # only the last two points will be ingested
    new_ids = sp.upsert_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            instrument_id=ztf_camera.id,
            mjd=[59400, 59401, 59402],
            mag=[19.2, 19.3, np.random.uniform(19, 20)],
            magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
            limiting_mag=[20.0, 20.1, 20.2],
            magsys=["ab", "ab", "ab"],
            filter=["ztfr", "ztfg", "ztfr"],
            ra=[42.01, 42.01, 42.02],
            dec=[42.02, 42.01, 42.03],
            origin=[None, "omg", "lol"],
            group_ids=[public_group.id],
        )
    ).ids
    assert len(new_ids) == 3
    assert len(set(new_ids).intersection(set(ids))) == 1

    # next we test the duplicate_ignore_flux + overwrite_flux arguments.
    # When duplicate_ignore_flux is True, the flux and fluxerr are not used when looking for existing
    # duplicates of the new datapoint we are trying to add.
    #
    # If overwrite_flux is also true, we do not just ignore the new datapoint
    # as we usually do, but we update the existing duplicate's flux and fluxerr.
    # This should ONLY work if the new datapoint and the existing duplicates have an origin specified.

    # so we send:
    # - same first point with different flux, should not be updated because the existing point does NOT have an origin
    # - same second point with different flux, should be updated because the existing poitn has an origin
    # - different third point, should be added as usual.
    ids = new_ids
    input_data = PhotometryPost(
        obj_id=str(public_source.id),
        instrument_id=ztf_camera.id,
        mjd=[59400, 59401, 59403],
        mag=[20.2, 20.3, np.random.uniform(18, 19)],
        magerr=[0.05, 0.1, np.random.uniform(0.01, 0.1)],
        limiting_mag=[21.0, 20.1, 20.2],
        magsys=["ab", "ab", "ab"],
        filter=["ztfr", "ztfg", "ztfr"],
        ra=[42.01, 42.01, 42.02],
        dec=[42.02, 42.01, 42.03],
        origin=[None, "omg", "lol"],
        group_ids=[public_group.id],
    )

    # this feature is reserved to super admin, so this should fail
    with pytest.raises(
        SkyPortalError,
        match="Ignoring flux/fluxerr when checking for duplicates is reserved to super admin users only",
    ) as err:
        sp.upsert_photometry(
            input_data, duplicate_ignore_flux=True, overwrite_flux=True
        )
    assert err.value.status_code == 400

    # try with the super admin token now
    new_ids = (
        client(super_admin_token)
        .upsert_photometry(input_data, duplicate_ignore_flux=True, overwrite_flux=True)
        .ids
    )
    assert len(new_ids) == 3
    # we should have 1 same + 1 updated - 1 new = 2 identical ids
    assert len(set(new_ids).intersection(set(ids))) == 2

    # GET the photometry
    # First point should be identical
    phot = client(upload_data_token).fetch_photometry_point(ids[0], format="mag")
    assert phot.mjd == 59400
    assert phot.mag == 19.2
    assert phot.magerr == 0.05

    # second point should be updated
    phot = client(upload_data_token).fetch_photometry_point(ids[1], format="mag")
    assert phot.mjd == 59401
    assert phot.mag == 20.3
    assert phot.magerr == 0.1


def test_token_user_post_put_get_photometry_data(
    upload_data_token_two_groups, public_source, public_group, public_group2, ztf_camera
):
    ids = (
        client(upload_data_token_two_groups)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                instrument_id=ztf_camera.id,
                mjd=[59400, 59401, 59402],
                mag=[19.2, 19.3, np.random.uniform(19, 20)],
                magerr=[0.05, 0.06, np.random.uniform(0.01, 0.1)],
                limiting_mag=[20.0, 20.1, 20.2],
                magsys=["ab", "ab", "ab"],
                filter=["ztfr", "ztfg", "ztfr"],
                ra=[42.01, 42.01, 42.02],
                dec=[42.02, 42.01, 42.03],
                origin=[None, "lol", "lol"],
                group_ids=[public_group.id],
            )
        )
        .ids
    )
    assert len(ids) == 3

    phot = client(upload_data_token_two_groups).fetch_photometry_point(
        ids[0], format="flux"
    )
    group_ids = [g.id for g in phot.groups]
    assert len(group_ids) == 2
    assert public_group.id in group_ids

    # PUTing photometry that contains
    # the same first point, the second point with a different origin, and a new third point should succeed
    # only the last two points will be ingested
    new_ids = (
        client(upload_data_token_two_groups)
        .upsert_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                instrument_id=ztf_camera.id,
                mjd=[59400, 59401],
                mag=[19.2, 19.3],
                magerr=[0.05, 0.06],
                limiting_mag=[20.0, 20.1],
                magsys=["ab", "ab"],
                filter=["ztfr", "ztfg"],
                ra=[42.01, 42.01],
                dec=[42.02, 42.01],
                origin=[None, "lol"],
                group_ids=[public_group.id, public_group2.id],
            )
        )
        .ids
    )
    assert len(new_ids) == 2
    assert len(set(new_ids).intersection(set(ids))) == 2

    phot = client(upload_data_token_two_groups).fetch_photometry_point(
        ids[0], format="flux"
    )
    group_ids = [g.id for g in phot.groups]
    assert len(group_ids) == 3

    token_object = (
        DBSession()
        .query(Token)
        .filter(Token.id == upload_data_token_two_groups)
        .first()
    )

    assert sorted(group_ids) == sorted(
        [
            public_group.id,
            public_group2.id,
            token_object.created_by.single_user_group.id,
        ]
    )


def test_post_photometry_multiple_groups(
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group,
    public_group2,
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
            group_ids=[public_group.id, public_group2.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")

    assert phot.ra is None
    assert phot.dec is None
    assert phot.ra_unc is None
    assert phot.dec_unc is None

    assert len(phot.groups) == 3

    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25.0 - 23.9)))


def test_post_photometry_all_groups(
    upload_data_token_two_groups,
    user_two_groups,
    super_admin_token,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
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
            )
        )
        .ids[0]
    )

    phot = client(super_admin_token).fetch_photometry_point(
        photometry_id, format="flux"
    )

    assert phot.ra is None
    assert phot.dec is None
    assert phot.ra_unc is None
    assert phot.dec_unc is None

    # Groups should be single user group and public group
    assert len(phot.groups) == 2
    groups = [g.name for g in phot.groups]
    assert cfg["misc"]["public_group_name"] in groups
    assert user_two_groups.single_user_group.name in groups

    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25.0 - 23.9)))


def test_retrieve_photometry_group_membership_posted_by_other(
    upload_data_token_two_groups,
    view_only_token,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
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
                group_ids=[public_group.id, public_group2.id],
            )
        )
        .ids[0]
    )

    phot = client(view_only_token).fetch_photometry_point(photometry_id, format="flux")

    assert phot.ra is None
    assert phot.dec is None
    assert phot.ra_unc is None
    assert phot.dec_unc is None

    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25.0 - 23.9)))


def test_retrieve_photometry_error_group_membership_posted_by_other(
    upload_data_token_two_groups,
    view_only_token,
    public_source_two_groups,
    public_group,
    public_group2,
    ztf_camera,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups
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
                group_ids=[public_group2.id],
            )
        )
        .ids[0]
    )
    # the upload_data_token user's single user group id is =
    # Token.query.get(upload_data_token).created_by.single_user_group.id

    # the view-only token group ids =
    # [g.id for g in Token.query.get(view_only_token).created_by.groups]

    # `view_only_token only` belongs to `public_group`, not `public_group2`
    with pytest.raises(
        SkyPortalError, match="Cannot find photometry point with ID"
    ) as err:
        client(view_only_token).fetch_photometry_point(photometry_id, format="flux")
    assert err.value.status_code == 400


def test_can_post_photometry_no_groups(
    upload_data_token, public_source, public_group, ztf_camera
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
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    assert len(phot.groups) == 1


def test_can_post_photometry_empty_groups_list(
    upload_data_token, public_source, public_group, ztf_camera
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
            group_ids=[],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    assert len(phot.groups) == 1


def test_token_user_post_mag_photometry_data_and_convert(
    upload_data_token, public_source, ztf_camera, public_group
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=21.0,
            magerr=0.2,
            limiting_mag=22.3,
            magsys="vega",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    correction = 2.5 * np.log10(vega.zpbandflux("ztfg") / ab.zpbandflux("ztfg"))

    np.testing.assert_allclose(phot.flux, 10 ** (-0.4 * (21.0 - correction - 23.9)))

    np.testing.assert_allclose(phot.fluxerr, 0.2 / (2.5 / np.log(10)) * phot.flux)

    phot = sp.fetch_photometry_point(photometry_id)

    np.testing.assert_allclose(phot.mag, 21.0 - correction)

    np.testing.assert_allclose(phot.magerr, 0.2)


def test_token_user_post_and_get_different_systems_mag(
    upload_data_token, public_source, ztf_camera, public_group
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=21.0,
            magerr=0.2,
            limiting_mag=22.3,
            magsys="vega",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="mag", magsys="vega")
    assert phot.magsys == "vega"

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    correction = 2.5 * np.log10(vega.zpbandflux("ztfg") / ab.zpbandflux("ztfg"))

    np.testing.assert_allclose(phot.mag, 21.0)
    np.testing.assert_allclose(phot.magerr, 0.2)
    np.testing.assert_allclose(phot.limiting_mag, 22.3)

    phot = sp.fetch_photometry_point(photometry_id, format="mag", magsys="ab")

    np.testing.assert_allclose(phot.mag, 21.0 - correction)
    np.testing.assert_allclose(phot.magerr, 0.2)
    np.testing.assert_allclose(phot.limiting_mag, 22.3 - correction)


def test_token_user_post_extinction_corrected_photometry(
    upload_data_token, public_source, ztf_camera, public_group
):
    from skyportal.utils.extinction import calculate_extinction

    a_lambda = calculate_extinction(public_source.ra, public_source.dec, "ztfg")
    assert a_lambda is not None and a_lambda > 0

    mag_in, mjd = 21.0, 58123.0

    # Upload as MW-extinction corrected: SkyPortal stores observed photometry, so
    # it re-reddens for storage.
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=mjd,
            instrument_id=ztf_camera.id,
            mag=mag_in,
            magerr=0.1,
            limiting_mag=22.5,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
            extinction_corrected=True,
        )
    ).ids[0]

    # Stored (observed) value is the uploaded mag re-reddened: mag_in + A_lambda.
    phot = sp.fetch_photometry_point(photometry_id, format="mag", magsys="ab")
    np.testing.assert_allclose(phot.mag, mag_in + a_lambda, rtol=1e-4)

    # Displaying with extinction correction dereddens back to the uploaded value.
    points = sp.fetch_photometry(
        public_source.id, format="mag", magsys="ab", include_extinction=True
    )
    point = next(p for p in points if p.mjd == mjd)
    np.testing.assert_allclose(point.mag_corr, mag_in, rtol=1e-4)


def test_token_user_post_uncorrected_photometry_unchanged(
    upload_data_token, public_source, ztf_camera, public_group
):
    # Without the flag, magnitudes are stored as-is (observed) -- the control.
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58124.0,
            instrument_id=ztf_camera.id,
            mag=21.0,
            magerr=0.1,
            limiting_mag=22.5,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]
    phot = sp.fetch_photometry_point(photometry_id, format="mag", magsys="ab")
    np.testing.assert_allclose(phot.mag, 21.0)


def test_token_user_post_and_get_different_systems_flux(
    upload_data_token, public_source, ztf_camera, public_group
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=21.0,
            magerr=0.2,
            limiting_mag=22.3,
            magsys="vega",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux", magsys="vega")

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    correction = 2.5 * np.log10(vega.zpbandflux("ztfg") / ab.zpbandflux("ztfg"))

    np.testing.assert_allclose(phot.flux, 10 ** (-0.4 * (21 - correction - 23.9)))
    np.testing.assert_allclose(phot.fluxerr, 0.2 / (2.5 / np.log(10)) * phot.flux)
    np.testing.assert_allclose(phot.zp, 23.9 + correction)

    phot = sp.fetch_photometry_point(photometry_id, format="flux", magsys="ab")

    np.testing.assert_allclose(phot.flux, 10 ** (-0.4 * (21 - correction - 23.9)))
    np.testing.assert_allclose(phot.fluxerr, 0.2 / (2.5 / np.log(10)) * phot.flux)
    np.testing.assert_allclose(phot.zp, 23.9)


def test_token_user_mixed_photometry_post(
    upload_data_token, public_source, ztf_camera, public_group
):
    photometry_id = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                mag=21.0,
                magerr=[0.2, 0.1],
                limiting_mag=22.3,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id],
            )
        )
        .ids[1]
    )

    phot = client(upload_data_token).fetch_photometry_point(
        photometry_id, format="flux"
    )

    np.testing.assert_allclose(phot.flux, 10 ** (-0.4 * (21.0 - 23.9)))

    np.testing.assert_allclose(phot.fluxerr, 0.1 / (2.5 / np.log(10)) * phot.flux)

    # should fail as len(mag) != len(magerr)
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": [21.0],
            "magerr": [0.2, 0.1],
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_token_user_mixed_mag_none_photometry_post(
    upload_data_token, public_source, ztf_camera, public_group
):
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": None,
            "magerr": [0.2, 0.1],
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": [21.3, None],
            "magerr": [0.2, 0.1],
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"

    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": [21.3, None],
            "magerr": [None, 0.1],
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_token_user_post_photometry_limits(
    upload_data_token, public_source, ztf_camera, public_group
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")

    assert phot.flux is None
    np.testing.assert_allclose(
        phot.fluxerr, 10 ** (-0.4 * (22.3 - 23.9)) / PHOT_DETECTION_THRESHOLD
    )

    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")

    assert phot.flux is None
    np.testing.assert_allclose(phot.fluxerr, 0.031 * 10 ** (-0.4 * (25.0 - 23.9)))


def test_token_user_post_invalid_filter(
    upload_data_token, public_source, ztf_camera, public_group
):
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token).post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                limiting_mag=22.3,
                magsys="ab",
                filter="bessellv",
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400


def test_token_user_post_photometry_data_series(
    upload_data_token, public_source, ztf_camera, public_group
):
    # valid request
    ids = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=[58000.0, 58001.0, 58002.0],
                instrument_id=ztf_camera.id,
                flux=[12.24, 15.24, 12.24],
                fluxerr=[0.031, 0.029, 0.030],
                filter=["ztfg", "ztfg", "ztfg"],
                zp=[25.0, 30.0, 21.2],
                magsys=["ab", "ab", "ab"],
                ra=264.1947917,
                dec=[50.5478333, 50.5478333 + 0.00001, 50.5478333],
                dec_unc=0.2,
                group_ids=[public_group.id],
            )
        )
        .ids
    )
    assert len(ids) == 3

    photometry_id = ids[1]
    phot = client(upload_data_token).fetch_photometry_point(
        photometry_id, format="flux"
    )
    assert np.allclose(phot.flux, 15.24 * 10 ** (-0.4 * (30 - 23.9)))

    assert np.allclose(phot.dec, 50.5478333 + 0.00001)

    assert np.allclose(phot.dec_unc, 0.2)
    assert phot.ra_unc is None

    # invalid request
    # raw api: intentionally malformed payload the typed client can't produce
    status, data = api(
        "POST",
        "photometry",
        data=[
            {
                "obj_id": str(public_source.id),
                "mjd": 58000,
                "instrument_id": ztf_camera.id,
                "flux": 12.24,
                "fluxerr": 0.031,
                "filter": "ztfg",
                "zp": 25.0,
                "magsys": "ab",
                "group_ids": [public_group.id],
            },
            {
                "obj_id": str(public_source.id),
                "mjd": 58001,
                "instrument_id": ztf_camera.id,
                "flux": 15.24,
                "fluxerr": 0.031,
                "filter": "ztfg",
                "zp": 30.0,
                "magsys": "ab",
                "group_ids": [public_group.id],
            },
            {
                "obj_id": str(public_source.id),
                "mjd": 58002,
                "instrument_id": ztf_camera.id,
                "flux": 12.24,
                "fluxerr": 0.031,
                "filter": "ztfg",
                "zp": 21.2,
                "magsys": "vega",
                "group_ids": [public_group.id],
            },
        ],
        token=upload_data_token,
    )

    assert status in [500, 401]
    assert data["status"] == "error"


def test_post_photometry_no_access_token(
    view_only_token, public_source, ztf_camera, public_group
):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_photometry(
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
        )
    assert err.value.status_code == 401


def test_token_user_update_photometry(
    upload_data_token, public_source, ztf_camera, public_group
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
            filter="ztfi",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    sp.update_photometry(
        photometry_id,
        PhotometryUpdate(
            obj_id=str(public_source.id),
            flux=11.0,
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfi",
        ),
    )

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    np.testing.assert_allclose(phot.flux, 11.0 * 10 ** (-0.4 * (25 - 23.9)))


def test_token_user_update_photometry_mag_to_nondetection(
    upload_data_token, public_source, ztf_camera, public_group
):
    # Upload a magnitude-space detection.
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=18.5,
            magerr=0.1,
            limiting_mag=22.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    # The photometry-edit form sends mag/magerr cleared (null) with a limiting_mag
    # and, for a point not tied to an observing-run assignment, omits the optional
    # assignment_id / ra_unc / dec_unc keys entirely. This used to 500 with a
    # KeyError because parse_mag/parse_flux read those keys directly under a
    # partial load.
    sp.update_photometry(
        photometry_id,
        PhotometryUpdate(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            mag=None,
            magerr=None,
            limiting_mag=22.0,
            magsys="ab",
            filter="ztfg",
        ),
    )

    phot = sp.fetch_photometry_point(photometry_id, format="mag")
    # mag+magerr removed -> it is now a non-detection with the limiting magnitude.
    assert phot.mag is None
    assert phot.magerr is None
    np.testing.assert_allclose(phot.limiting_mag, 22.0)


def test_token_user_cannot_update_unowned_photometry(
    upload_data_token, manage_sources_token, public_source, ztf_camera, public_group
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
            filter="ztfi",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).update_photometry(
            photometry_id,
            PhotometryUpdate(
                obj_id=str(public_source.id),
                flux=11.0,
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfi",
            ),
        )
    assert err.value.status_code == 401


def test_token_user_update_photometry_groups(
    upload_data_token_two_groups,
    manage_sources_token_two_groups,
    public_source_two_groups,
    ztf_camera,
    public_group,
    public_group2,
    view_only_token,
):
    upload_data_token = upload_data_token_two_groups
    public_source = public_source_two_groups

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
                filter="ztfi",
                group_ids=[public_group.id, public_group2.id],
            )
        )
        .ids[0]
    )

    client(view_only_token).fetch_photometry_point(photometry_id, format="flux")

    client(upload_data_token).update_photometry(
        photometry_id,
        PhotometryUpdate(
            obj_id=str(public_source.id),
            flux=11.0,
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfi",
            group_ids=[public_group2.id],
        ),
    )

    with pytest.raises(
        SkyPortalError, match="Cannot find photometry point with ID"
    ) as err:
        client(view_only_token).fetch_photometry_point(photometry_id, format="flux")
    assert err.value.status_code == 400


def test_user_can_delete_owned_photometry_data(
    upload_data_token, public_source, ztf_camera, public_group
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
            filter="ztfi",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    sp.delete_photometry(photometry_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_photometry_point(photometry_id, format="flux")
    assert err.value.status_code == 400


def test_user_cannot_delete_unowned_photometry_data(
    upload_data_token, manage_sources_token, public_source, ztf_camera, public_group
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
            filter="ztfi",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).delete_photometry(photometry_id)
    assert err.value.status_code == 401


def test_admin_can_delete_unowned_photometry_data(
    upload_data_token, super_admin_token, public_source, ztf_camera, public_group
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
            filter="ztfi",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    np.testing.assert_allclose(phot.flux, 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    client(super_admin_token).delete_photometry(photometry_id)

    with pytest.raises(SkyPortalError) as err:
        sp.fetch_photometry_point(photometry_id, format="flux")
    assert err.value.status_code == 400


def test_token_user_retrieving_source_photometry_and_convert(
    view_only_token, public_source
):
    sp = client(view_only_token)
    points = sp.fetch_photometry(public_source.id, format="flux", magsys="ab")
    assert isinstance(points, list)
    assert "mjd" in points[0].model_fields_set
    assert "ra_unc" in points[0].model_fields_set

    points = sorted(points, key=lambda p: p.mjd)
    mag1_ab = -2.5 * np.log10(points[0].flux) + points[0].zp
    magerr1_ab = 2.5 / np.log(10) * points[0].fluxerr / points[0].flux

    maglast_ab = -2.5 * np.log10(points[-1].flux) + points[-1].zp
    magerrlast_ab = 2.5 / np.log(10) * points[-1].fluxerr / points[-1].flux

    points = sp.fetch_photometry(public_source.id, format="mag", magsys="ab")

    points = sorted(points, key=lambda p: p.mjd)
    assert np.allclose(mag1_ab, points[0].mag)
    assert np.allclose(magerr1_ab, points[0].magerr)

    assert np.allclose(maglast_ab, points[-1].mag)
    assert np.allclose(magerrlast_ab, points[-1].magerr)

    points = sp.fetch_photometry(public_source.id, format="flux", magsys="vega")

    points = sorted(points, key=lambda p: p.mjd)
    mag1_vega = -2.5 * np.log10(points[0].flux) + points[0].zp
    magerr1_vega = 2.5 / np.log(10) * points[0].fluxerr / points[0].flux

    maglast_vega = -2.5 * np.log10(points[-1].flux) + points[-1].zp
    magerrlast_vega = 2.5 / np.log(10) * points[-1].fluxerr / points[-1].flux

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    vega_to_ab = {
        filter: 2.5 * np.log10(ab.zpbandflux(filter) / vega.zpbandflux(filter))
        for filter in ["ztfg", "ztfr", "ztfi"]
    }

    assert np.allclose(mag1_ab, mag1_vega + vega_to_ab[points[0].filter])
    assert np.allclose(magerr1_ab, magerr1_vega)

    assert np.allclose(maglast_ab, maglast_vega + vega_to_ab[points[-1].filter])
    assert np.allclose(magerrlast_ab, magerrlast_vega)


def test_source_photometry_format_plot_is_slim(view_only_token, public_source):
    """``format=plot`` must return only the lightcurve-plotter fields and
    match the magnitudes that ``format=mag`` produces."""
    # skyportal-py gap: typed models cannot expose raw JSON keys (format=plot key-set check)
    status, plot_resp = api(
        "GET",
        f"sources/{public_source.id}/photometry?format=plot&magsys=ab",
        token=view_only_token,
    )
    assert status == 200
    assert plot_resp["status"] == "success"
    assert isinstance(plot_resp["data"], list)
    assert len(plot_resp["data"]) > 0

    allowed_keys = {
        "id",
        "obj_id",
        "filter",
        "mjd",
        "origin",
        "mag",
        "magerr",
        "limiting_mag",
    }
    for point in plot_resp["data"]:
        assert set(point.keys()) == allowed_keys, (
            f"format=plot returned unexpected keys: {set(point.keys()) - allowed_keys}; "
            f"missing: {allowed_keys - set(point.keys())}"
        )

    mag_points = client(view_only_token).fetch_photometry(
        public_source.id, format="mag", magsys="ab"
    )

    mag_by_id = {p.id: p for p in mag_points}
    assert {p["id"] for p in plot_resp["data"]} == set(mag_by_id), (
        "format=plot and format=mag returned different photometry IDs"
    )
    for plot_point in plot_resp["data"]:
        mag_point = mag_by_id[plot_point["id"]]
        for field in ("mag", "magerr", "limiting_mag"):
            if getattr(mag_point, field) is None:
                assert plot_point[field] is None
            else:
                assert np.allclose(plot_point[field], getattr(mag_point, field))


def test_token_user_retrieve_null_photometry(
    upload_data_token, public_source, ztf_camera, public_group
):
    sp = client(upload_data_token)
    photometry_id = sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    ).ids[0]

    phot = sp.fetch_photometry_point(photometry_id, format="flux")
    assert phot.flux is None

    np.testing.assert_allclose(
        phot.fluxerr, 10 ** (-0.4 * (22.3 - 23.9)) / PHOT_DETECTION_THRESHOLD
    )

    phot = sp.fetch_photometry_point(photometry_id, format="mag")
    assert phot.mag is None
    assert phot.magerr is None


def test_token_user_get_range_photometry(
    upload_data_token, public_source, public_group, ztf_camera
):
    sp = client(upload_data_token)
    sp.post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=[58000.0, 58500.0, 59000.0],
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    points = sp.fetch_photometry_range(
        instrument_ids=[ztf_camera.id], max_date="2018-05-15T00:00:00"
    )
    assert len(points) == 1

    points = sp.fetch_photometry_range(
        instrument_ids=[ztf_camera.id],
        max_date="2019-02-01T00:00:00",
        format="flux",
        magsys="vega",
    )
    assert len(points) == 2


def test_token_user_post_to_foreign_group_and_retrieve(
    upload_data_token, public_source_two_groups, public_group2, ztf_camera
):
    photometry_id = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=str(public_source_two_groups.id),
                mjd=[58000.0, 58500.0, 59000.0],
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group2.id],
            )
        )
        .ids[0]
    )
    client(upload_data_token).fetch_photometry_point(photometry_id, format="flux")


@pytest.mark.flaky(reruns=2, reruns_delay=5)
def test_problematic_photometry_1263(
    upload_data_token, public_source, public_group, ztf_camera, public_group2
):
    payload = {
        "obj_id": public_source.id,
        "group_ids": [public_group.id, public_group2.id],
        "magsys": "ab",
        "zp": 23.9,
        "instrument_id": ztf_camera.id,
        "mjd": [
            59145.46447,
            59149.50347,
            59149.50347,
            59150.50872,
            59150.50872,
            59152.51631,
            59155.50801,
            59152.51631,
            59155.50801,
            59156.48479,
            59156.48479,
            59126.48693,
            59128.46834,
            59130.50257,
            59135.47329,
            59137.4758,
            59139.45454,
            59141.47449,
            59143.50987,
            59143.50987,
            59145.46447,
            59145.50556,
            59150.52806,
            59150.52806,
            59151.52116,
            59151.52116,
            59152.48332,
            59152.48332,
            59155.50022,
            59155.50022,
            59156.5383,
            59126.53144,
            59128.51928,
            59130.53196,
            59135.51196,
            59137.51334,
            59139.51507,
            59141.51422,
            59143.48529,
            59143.48529,
            59145.50556,
        ],
        "filter": [
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
        ],
        "flux": [
            105.4095462,
            100.4989583,
            100.4986052,
            97.45052422,
            97.45411937,
            91.71425204,
            81.08011148,
            91.71489652,
            81.08110854,
            59.37327478,
            59.37452643,
            None,
            None,
            None,
            73.17457336,
            82.20150344,
            89.14970986,
            102.1692537,
            98.6103674,
            98.60984771,
            105.4086204,
            100.8602976,
            94.84847105,
            94.85063718,
            104.8945366,
            104.8961951,
            101.6093671,
            101.6061542,
            82.34545782,
            82.34560248,
            72.48165796,
            None,
            None,
            None,
            61.60270207,
            72.73101786,
            83.83015488,
            98.70066264,
            99.85275375,
            99.84977174,
            100.8608292,
        ],
        "fluxerr": [
            8.416851743,
            10.10817406,
            10.10811785,
            11.74314252,
            11.74356103,
            11.40505647,
            10.61680918,
            11.40514417,
            10.61696199,
            10.6736128,
            10.67382477,
            13.51668635,
            18.71327665,
            9.509339593,
            9.374956127,
            9.638764985,
            11.98599464,
            10.42671307,
            9.666542673,
            9.666476165,
            8.41682049,
            8.680180822,
            9.926401394,
            9.926617677,
            8.494021784,
            8.494115051,
            9.984017125,
            9.983686084,
            7.964270439,
            7.964306468,
            8.499519049,
            12.65289244,
            11.39803573,
            9.771246706,
            7.839855173,
            7.592658663,
            8.674127848,
            8.965488502,
            7.69135795,
            7.691126885,
            8.680212034,
        ],
    }

    client(upload_data_token).post_photometry(PhotometryPost(**payload))

    payload = {
        "obj_id": public_source.id,
        "group_ids": "all",
        "magsys": "ab",
        "instrument_id": ztf_camera.id,
        "filter": [
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfg",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfg",
            "ztfr",
        ],
        "mjd": [
            59130.53195599979,
            59135.473286999855,
            59135.51195599977,
            59137.47579859989,
            59137.51334490022,
            59139.45453700004,
            59139.51506939996,
            59141.474490699824,
            59141.51422449993,
            59143.48528939998,
            59143.50987270009,
            59145.46446759999,
            59145.50555559993,
            59149.50347220013,
            59150.50871529989,
            59150.52805559989,
            59151.52115740022,
            59152.4833217999,
            59152.516307900194,
            59155.50021990016,
            59155.5080093001,
            59156.4847916998,
            59156.53829859989,
        ],
        "limiting_mag": [
            19.67770004272461,
            20.11709976196289,
            20.059200286865234,
            20.281099319458008,
            20.224000930786133,
            19.809099197387695,
            20.236799240112305,
            20.57659912109375,
            20.31290054321289,
            20.414499282836914,
            20.680700302124023,
            20.57069969177246,
            20.48349952697754,
            20.242000579833984,
            20.642900466918945,
            20.029699325561523,
            20.11090087890625,
            19.808948516845703,
            19.819171905517578,
            19.9112606048584,
            19.913991928100586,
            19.600677490234375,
            20.005773544311523,
        ],
        "mag": [
            None,
            19.239099502563477,
            19.426000595092773,
            19.11280059814453,
            19.24570083618164,
            19.024700164794922,
            19.09149932861328,
            18.876699447631836,
            18.914199829101562,
            18.901599884033203,
            18.915199279785156,
            18.84280014038086,
            18.89069938659668,
            18.89459991455078,
            18.92799949645996,
            18.957399368286133,
            18.848100662231445,
            18.882665634155273,
            18.993907928466797,
            19.110898971557617,
            19.127714157104492,
            19.466022491455078,
            19.24942970275879,
        ],
        "magerr": [
            None,
            0.1391019970178604,
            0.13817599415779114,
            0.12731100618839264,
            0.11334399878978729,
            0.1459749937057495,
            0.11234399676322937,
            0.11080300062894821,
            0.09862300008535385,
            0.0836310014128685,
            0.1064319983124733,
            0.08669500052928925,
            0.09344000369310379,
            0.10920300334692001,
            0.13083499670028687,
            0.11362800002098083,
            0.08791899681091309,
            0.1066831648349762,
            0.13501590490341187,
            0.10501029342412949,
            0.14216870069503784,
            0.19518424570560455,
            0.12731821835041046,
        ],
        "ra": [
            None,
            134.5934039,
            134.5934169,
            134.5933773,
            134.593404,
            134.593372,
            134.5933825,
            134.5933984,
            134.5933945,
            134.5933917,
            134.5933988,
            134.5933848,
            134.5933991,
            134.5933909,
            134.5934048,
            134.5934296,
            134.5934341,
            134.593388,
            134.5933606,
            134.5933857,
            134.5933939,
            134.5933847,
            134.5933954,
        ],
        "dec": [
            None,
            15.0412865,
            15.041256,
            15.0412686,
            15.0412482,
            15.0412709,
            15.0412572,
            15.0412656,
            15.0412765,
            15.0412744,
            15.0412673,
            15.041271,
            15.0412726,
            15.0413061,
            15.0412751,
            15.041267,
            15.0412856,
            15.0412655,
            15.0412913,
            15.0412952,
            15.0412737,
            15.0411913,
            15.0412605,
        ],
    }

    client(upload_data_token).post_photometry(PhotometryPost(**payload))

    payload["group_ids"] = "all"

    ids = client(upload_data_token).upsert_photometry(PhotometryPost(**payload)).ids

    for id in ids:
        phot = client(upload_data_token).fetch_photometry_point(id, format="flux")
        assert len(phot.groups) == 2


def test_problematic_photometry_1276(
    public_source, public_group, super_admin_token, ztf_camera
):
    payload = {
        "obj_id": public_source.id,
        "group_ids": [public_group.id],
        "magsys": "ab",
        "instrument_id": ztf_camera.id,
        "filter": [
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfg",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfr",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfg",
            "ztfr",
            "ztfr",
            "ztfg",
            "ztfg",
            "ztfr",
            "ztfg",
            "ztfr",
        ],
        "mjd": [
            59123.41299769981,
            59129.472291700076,
            59134.451203700155,
            59136.46903940011,
            59136.46903940011,
            59139.295057899784,
            59139.295057899784,
            59139.295057899784,
            59139.389629600104,
            59141.36341439979,
            59141.36341439979,
            59141.414189800154,
            59141.414189800154,
            59143.318460599985,
            59143.39145829994,
            59145.34545140015,
            59145.34545140015,
            59145.34545140015,
            59145.41583329998,
            59145.41583329998,
            59149.4703819002,
            59151.32671299996,
            59151.33918979997,
            59153.33692129981,
            59153.404351899866,
            59155.220972199924,
            59155.290161999874,
            59157.360347200185,
            59157.433634299785,
        ],
        "limiting_mag": [
            19.396099090576172,
            20.23240089416504,
            20.129100799560547,
            20.493600845336914,
            20.493600845336914,
            20.422000885009766,
            20.422000885009766,
            20.422000885009766,
            20.272199630737305,
            20.18910026550293,
            20.18910026550293,
            20.846799850463867,
            20.846799850463867,
            20.624300003051758,
            20.854000091552734,
            20.628799438476562,
            20.628799438476562,
            20.628799438476562,
            20.840900421142578,
            20.840900421142578,
            20.32859992980957,
            19.60849952697754,
            19.705799102783203,
            19.47800064086914,
            19.409400939941406,
            19.462600708007812,
            19.77630043029785,
            19.678672790527344,
            19.754121780395508,
        ],
        "mag": [
            18.43560028076172,
            17.338199615478516,
            16.25189971923828,
            16.011999130249023,
            16.09589958190918,
            15.974100112915039,
            15.891500473022461,
            15.891500473022461,
            None,
            15.753999710083008,
            15.819600105285645,
            18.528499603271484,
            18.57939910888672,
            15.781000137329102,
            18.309499740600586,
            15.692399978637695,
            15.692399978637695,
            15.790599822998047,
            18.305700302124023,
            18.31529998779297,
            18.13994026184082,
            18.040000915527344,
            15.505499839782715,
            15.569299697875977,
            17.812599182128906,
            18.046100616455078,
            None,
            17.95865249633789,
            15.475956916809082,
        ],
        "magerr": [
            0.18098600208759308,
            0.12704600393772125,
            0.03412500023841858,
            0.018530000001192093,
            0.09321600198745728,
            0.1358170062303543,
            0.017785999923944473,
            0.017785999923944473,
            None,
            0.017010999843478203,
            0.0650859996676445,
            0.1969199925661087,
            0.08772700279951096,
            0.05595200136303902,
            0.17250700294971466,
            0.0137339998036623,
            0.0137339998036623,
            0.06520400196313858,
            0.06727799773216248,
            0.13235700130462646,
            0.12975013256072998,
            0.11010699719190598,
            0.04597700014710426,
            0.049855999648571014,
            0.10752200335264206,
            0.13239599764347076,
            None,
            0.139614999294281,
            0.042450759559869766,
        ],
        "ra": [
            56.0478815,
            56.0468989,
            56.0478,
            56.0478343,
            56.0480658,
            56.0475873,
            56.047908,
            56.0480877,
            None,
            56.0476469,
            56.0477499,
            56.047177,
            56.0469751,
            56.0480999,
            56.0470656,
            56.0477652,
            56.0476761,
            56.0476218,
            56.0469908,
            56.0472491,
            56.0467978,
            56.0472009,
            56.0478524,
            56.0476997,
            56.0471999,
            56.0476057,
            None,
            56.0473734,
            56.0477336,
        ],
        "dec": [
            71.6368125,
            71.6367721,
            71.6367167,
            71.6367615,
            71.6367048,
            71.6368681,
            71.6368457,
            71.6368389,
            None,
            71.6367596,
            71.6365229,
            71.6367611,
            71.6368439,
            71.6367764,
            71.6368222,
            71.6367943,
            71.6368108,
            71.6367366,
            71.6368412,
            71.6367895,
            71.6368039,
            71.6367984,
            71.6367866,
            71.6367788,
            71.6368348,
            71.6367571,
            None,
            71.6367753,
            71.6367119,
        ],
    }

    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).upsert_photometry(PhotometryPost(**payload))
    assert err.value.status_code in [400, 500]


def test_cannot_post_negative_fluxerr(
    upload_data_token, public_source, public_group, ztf_camera
):
    with pytest.raises(SkyPortalError, match="Invalid value") as err:
        client(upload_data_token).post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                flux=12.24,
                fluxerr=-0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id],
                altdata={"some_key": "some_value"},
            )
        )
    assert err.value.status_code == 400

    with pytest.raises(SkyPortalError, match="Invalid value") as err:
        client(upload_data_token).post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=[58000.0, 58000.4],
                instrument_id=ztf_camera.id,
                flux=[12.24, 12.43],
                fluxerr=[0.35, -0.031],
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id],
                altdata={"some_key": "some_value"},
            )
        )
    assert err.value.status_code == 400


def test_photometry_stream_read_access(
    upload_data_token,
    view_only_token_no_groups,
    view_only_token_no_groups_no_streams,
    public_source,
    public_stream,
    ztf_camera,
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
                stream_ids=[public_stream.id],
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    # this token has sufficient stream access
    client(view_only_token_no_groups).fetch_photometry_point(photometry_id)

    # this token does not have sufficient stream access
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token_no_groups_no_streams).fetch_photometry_point(
            photometry_id
        )
    assert err.value.status_code == 400


def test_photometry_stream_post_access(
    upload_data_token_no_groups,
    upload_data_token_no_groups_no_streams,
    public_source,
    public_stream,
    ztf_camera,
):
    # this token has sufficient stream access to create a StreamPhotometry row
    client(upload_data_token_no_groups).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            stream_ids=[public_stream.id],
            altdata={"some_key": "some_value"},
        )
    )

    # this token doesn't have sufficient stream access to create a StreamPhotometry row
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_no_groups_no_streams).post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58001.0,
                instrument_id=ztf_camera.id,
                flux=13.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                stream_ids=[public_stream.id],
                altdata={"some_key": "some_value"},
            )
        )
    assert err.value.status_code == 400


def test_photometry_stream_put_access(
    upload_data_token_no_groups,
    upload_data_token_no_groups_no_streams,
    upload_data_token_stream2,
    public_source,
    public_stream,
    public_stream2,
    ztf_camera,
):
    # this token has sufficient stream access to create a StreamPhotometry row
    client(upload_data_token_no_groups).post_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            flux=12.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            stream_ids=[public_stream.id],
            altdata={"some_key": "some_value"},
        )
    )

    # this token doesn't have sufficient stream access to add to stream2
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_no_groups_no_streams).upsert_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58001.0,
                instrument_id=ztf_camera.id,
                flux=13.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                stream_ids=[public_stream2.id],
                altdata={"some_key": "some_value"},
            )
        )
    assert err.value.status_code == 400

    # this token doesn't have sufficient stream access to create a StreamPhotometry row
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_no_groups).upsert_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=58001.0,
                instrument_id=ztf_camera.id,
                flux=13.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                stream_ids=[public_stream2.id],
                altdata={"some_key": "some_value"},
            )
        )
    assert err.value.status_code == 400

    # this token does have sufficient stream access to add to stream2
    client(upload_data_token_stream2).upsert_photometry(
        PhotometryPost(
            obj_id=str(public_source.id),
            mjd=58001.0,
            instrument_id=ztf_camera.id,
            flux=13.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            stream_ids=[public_stream2.id],
            altdata={"some_key": "some_value"},
        )
    )


def test_photometry_stream_patch_access(
    upload_data_token_no_groups,
    upload_data_token_no_groups_no_streams,
    upload_data_token_no_groups_two_streams,
    public_source,
    public_stream,
    public_stream2,
    ztf_camera,
):
    # this token has sufficient stream access to create a StreamPhotometry row
    phot_id = (
        client(upload_data_token_no_groups_two_streams)
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
                stream_ids=[public_stream.id],
                altdata={"some_key": "some_value"},
            )
        )
        .ids[0]
    )

    # this token doesn't have sufficient stream access to add to stream2
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_no_groups_no_streams).update_photometry(
            phot_id,
            PhotometryUpdate(
                obj_id=str(public_source.id),
                mjd=58001.0,
                instrument_id=ztf_camera.id,
                flux=13.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                stream_ids=[public_stream2.id],
                altdata={"some_key": "some_value"},
            ),
        )
    assert err.value.status_code == 400

    # this token doesn't have sufficient stream access to create a StreamPhotometry row
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token_no_groups).update_photometry(
            phot_id,
            PhotometryUpdate(
                obj_id=str(public_source.id),
                mjd=58001.0,
                instrument_id=ztf_camera.id,
                flux=13.24,
                fluxerr=0.031,
                zp=25.0,
                magsys="ab",
                filter="ztfg",
                stream_ids=[public_stream2.id],
                altdata={"some_key": "some_value"},
            ),
        )
    assert err.value.status_code == 400

    # this token does have sufficient stream access to add to stream2
    client(upload_data_token_no_groups_two_streams).update_photometry(
        phot_id,
        PhotometryUpdate(
            obj_id=str(public_source.id),
            mjd=58001.0,
            instrument_id=ztf_camera.id,
            flux=13.24,
            fluxerr=0.031,
            zp=25.0,
            magsys="ab",
            filter="ztfg",
            stream_ids=[public_stream2.id],
            altdata={"some_key": "some_value"},
        ),
    )


def test_token_user_delete_object_photometry(
    super_admin_token, upload_data_token, view_only_token, ztf_camera, public_group
):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            group_ids=[public_group.id],
        )
    )

    client(upload_data_token).post_photometry(
        PhotometryPost(
            obj_id=obj_id,
            mjd=58000.0,
            instrument_id=ztf_camera.id,
            limiting_mag=22.3,
            magsys="ab",
            filter="ztfg",
            group_ids=[public_group.id],
        )
    )

    points = client(view_only_token).fetch_photometry(obj_id)
    assert len(points) > 0

    client(super_admin_token).delete_source_photometry(obj_id)

    points = client(view_only_token).fetch_photometry(obj_id)
    assert len(points) == 0


def test_photometry_validation(
    super_admin_token, upload_data_token, view_only_token, ztf_camera, public_group
):
    obj_id = str(uuid.uuid4())
    client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            redshift=3,
            group_ids=[public_group.id],
        )
    )

    photometry_id = (
        client(upload_data_token)
        .post_photometry(
            PhotometryPost(
                obj_id=obj_id,
                mjd=58000.0,
                instrument_id=ztf_camera.id,
                limiting_mag=22.3,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id],
            )
        )
        .ids[0]
    )

    # insufficient access, should fail
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_photometry_validation(
            photometry_id,
            validated=True,
            explanation="GOOD SUBTRACTION",
            notes="beautiful image",
        )
    assert err.value.status_code == 401

    client(super_admin_token).post_photometry_validation(
        photometry_id,
        validated=True,
        explanation="GOOD SUBTRACTION",
        notes="beautiful image",
    )

    points = client(view_only_token).fetch_photometry(
        obj_id, include_validation_info=True
    )
    assert len(points) > 0
    assert len(points[0].validations) > 0
    assert points[0].validations[0].explanation == "GOOD SUBTRACTION"
    assert points[0].validations[0].notes == "beautiful image"
    assert points[0].validations[0].validated is True

    client(super_admin_token).update_photometry_validation(
        photometry_id,
        validated=False,
        explanation="BAD SUBTRACTION",
        notes="ugly image",
    )

    points = client(view_only_token).fetch_photometry(
        obj_id, include_validation_info=True
    )
    assert len(points) > 0
    assert len(points[0].validations) > 0
    assert points[0].validations[0].explanation == "BAD SUBTRACTION"
    assert points[0].validations[0].notes == "ugly image"
    assert points[0].validations[0].validated is False

    client(super_admin_token).delete_photometry_validation(photometry_id)

    points = client(view_only_token).fetch_photometry(
        obj_id, include_validation_info=True
    )
    assert len(points) > 0
    assert len(points[0].validations) == 0


def test_post_external_photometry(
    upload_data_token, super_admin_token, super_admin_user, public_group
):
    obj_id = str(uuid.uuid4())
    source = client(upload_data_token).post_source(
        SourcePost(
            id=obj_id,
            ra=234.22,
            dec=-22.33,
            group_ids=[public_group.id],
        )
    )
    assert source.id == obj_id

    name = str(uuid.uuid4())
    telescope_id = (
        client(super_admin_token)
        .post_telescope(
            TelescopePost(
                name=name,
                nickname=name,
                lat=0.0,
                lon=0.0,
                elevation=0.0,
                diameter=10.0,
            )
        )
        .id
    )

    instrument_name = str(uuid.uuid4())
    instrument_id = (
        client(super_admin_token)
        .post_instrument(
            InstrumentPost(
                name=instrument_name,
                type="imager",
                band="NIR",
                filters=["atlaso", "atlasc"],
                telescope_id=telescope_id,
            )
        )
        .id
    )

    datafile = f"{os.path.dirname(__file__)}/../../data/ZTFrlh6cyjh_ATLAS.csv"
    df = pd.read_csv(datafile)
    df.drop(columns=["index"], inplace=True)

    data_out = {
        "obj_id": obj_id,
        "instrument_id": instrument_id,
        "group_ids": "all",
        **df.to_dict(orient="list"),
    }

    async def _call():
        async with baselayer_models.async_plain_session_factory() as s:
            u = await s.get(User, super_admin_user.id)
            await add_external_photometry(data_out, u, s)

    asyncio.run(_call())

    # Check the photometry sent back with the source
    fetched = client(super_admin_token).fetch_source(obj_id, include_photometry=True)
    assert len(fetched.photometry) == 384

    assert all(p.obj_id == obj_id for p in fetched.photometry)
    assert all(p.instrument_id == instrument_id for p in fetched.photometry)


def test_token_user_big_post(
    upload_data_token, public_source, ztf_camera, public_group
):
    with pytest.raises(SkyPortalError) as err:
        client(upload_data_token).post_photometry(
            PhotometryPost(
                obj_id=str(public_source.id),
                mjd=[58000 + i for i in range(30000)],
                instrument_id=ztf_camera.id,
                mag=np.random.uniform(low=18, high=22, size=30000).tolist(),
                magerr=np.random.uniform(low=0.1, high=0.3, size=30000).tolist(),
                limiting_mag=22.3,
                magsys="ab",
                filter="ztfg",
                group_ids=[public_group.id],
            )
        )
    assert err.value.status_code == 400
    assert (
        str(err.value)
        == "Maximum number of photometry rows to post exceeded: 30000 > 10000. Please break up the data into smaller sets and try again"
    )


def _build_params(obj_id, instrument_id, user_id, mjd_offset=0, flux=100.0):
    """Construct minimal Photometry param dicts for bulk_upsert_photometry.

    All Photometry NOT NULL columns are populated; non-dedup fields are kept
    distinct from defaults so we can detect updates.
    """
    now = utcnow_naive()
    return [
        {
            "obj_id": obj_id,
            "instrument_id": instrument_id,
            "mjd": 59000.0 + mjd_offset + i,
            "flux": flux,
            "fluxerr": 2.0,
            "filter": "ztfr",
            "origin": "bulk-upsert-test",
            "ra": 10.0,
            "dec": 20.0,
            "ra_unc": None,
            "dec_unc": None,
            "altdata": None,
            "original_user_data": None,
            "upload_id": str(uuid.uuid4()),
            "owner_id": user_id,
            "ref_flux": None,
            "ref_fluxerr": None,
            "created_at": now,
            "modified": now,
        }
        for i in range(3)
    ]


def test_bulk_upsert_photometry_error_mode(public_source, ztf_camera, user):
    """duplicates="error": first insert succeeds; re-inserting any
    overlapping row raises ValidationError listing the dedup keys."""
    params = _build_params(public_source.id, ztf_camera.id, user.id, mjd_offset=100)

    async def _body():
        async with baselayer_models.async_plain_session_factory() as session:
            ids = await bulk_upsert_photometry(session, params, duplicates="error")
            await session.commit()
            assert len(ids) == 3
            assert all(isinstance(i, int) for i in ids)

            # Second call with overlapping dedup keys should raise
            with pytest.raises(MMValidationError) as excinfo:
                await bulk_upsert_photometry(session, params, duplicates="error")
            await session.rollback()
            assert "already exists" in str(excinfo.value)

            await session.execute(sa.delete(Photometry).where(Photometry.id.in_(ids)))
            await session.commit()

    asyncio.run(_body())


def test_bulk_upsert_photometry_ignore_mode(public_source, ztf_camera, user):
    """duplicates="ignore": re-inserting overlapping rows is a no-op;
    returns the IDs of the existing rows in input order."""
    params = _build_params(public_source.id, ztf_camera.id, user.id, mjd_offset=200)

    async def _body():
        async with baselayer_models.async_plain_session_factory() as session:
            first_ids = await bulk_upsert_photometry(
                session, params, duplicates="ignore"
            )
            await session.commit()
            assert len(first_ids) == 3

            # Re-call with same params — should not raise, should return same IDs
            second_ids = await bulk_upsert_photometry(
                session, params, duplicates="ignore"
            )
            await session.commit()
            assert second_ids == first_ids

            await session.execute(
                sa.delete(Photometry).where(Photometry.id.in_(first_ids))
            )
            await session.commit()

    asyncio.run(_body())


def test_bulk_upsert_photometry_update_mode(public_source, ztf_camera, user):
    """duplicates="update": overlapping dedup keys atomically update the
    non-key columns. Verify a non-key field (ra) is overwritten."""
    params = _build_params(public_source.id, ztf_camera.id, user.id, mjd_offset=300)

    async def _body():
        async with baselayer_models.async_plain_session_factory() as session:
            ids = await bulk_upsert_photometry(session, params, duplicates="update")
            await session.commit()
            assert len(ids) == 3

            # Mutate non-key column and re-upsert
            new_ra = 99.5
            for p in params:
                p["ra"] = new_ra
            updated_ids = await bulk_upsert_photometry(
                session, params, duplicates="update"
            )
            await session.commit()
            assert updated_ids == ids  # same rows

            # Verify the update actually landed
            rows = (
                await session.scalars(
                    sa.select(Photometry).where(Photometry.id.in_(ids))
                )
            ).all()
            assert all(r.ra == new_ra for r in rows)

            await session.execute(sa.delete(Photometry).where(Photometry.id.in_(ids)))
            await session.commit()

    asyncio.run(_body())


def test_get_photometry_without_id_returns_error(upload_data_token):
    # A bare GET /api/photometry (id is optional in the route, shared with POST)
    # must return a clean error, not crash with a TypeError.
    # raw api: intentionally malformed request the typed client can't produce
    status, data = api("GET", "photometry", token=upload_data_token)
    assert status == 400
