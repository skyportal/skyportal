import os
import uuid

import numpy as np
import pandas as pd
import sncosmo
import sqlalchemy as sa

from baselayer.app.env import load_env
from skyportal.handlers.api.photometry import add_external_photometry
from skyportal.models import DBSession, Token
from skyportal.models.photometry import Photometry
from skyportal.tests import api, assert_api

_, cfg = load_env()
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


def test_token_user_post_get_photometry_data(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["ra"] is None
    assert data["data"]["dec"] is None
    assert data["data"]["ra_unc"] is None
    assert data["data"]["dec_unc"] is None
    assert data["data"]["altdata"] == {"some_key": "some_value"}

    np.testing.assert_allclose(
        data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_ref_flux(upload_data_token, public_source, public_group, ztf_camera):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58003.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "ref_flux": 8.01,
            "ref_fluxerr": 0.01,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=both", token=upload_data_token
    )
    assert_api(status, data)

    assert data["data"]["ra"] is None
    assert data["data"]["dec"] is None
    assert data["data"]["ra_unc"] is None
    assert data["data"]["dec_unc"] is None
    assert data["data"]["altdata"] == {"some_key": "some_value"}

    # correct for the difference in zeropoints
    corrected_flux = 12.24 / 10 ** (0.4 * (25.0 - 23.9))
    corrected_fluxerr = 0.031 / 10 ** (0.4 * (25.0 - 23.9))
    assert np.isclose(data["data"]["flux"], corrected_flux)
    assert data["data"]["fluxerr"] == corrected_fluxerr
    assert data["data"]["ref_flux"] == 8.01
    assert data["data"]["ref_fluxerr"] == 0.01
    assert data["data"]["tot_flux"] == 8.01 + corrected_flux
    assert data["data"]["tot_fluxerr"] == np.sqrt(corrected_fluxerr**2 + 0.01**2)

    # what about magnitudes?
    assert np.isclose(data["data"]["mag"], -2.5 * np.log10(corrected_flux) + 23.9)
    assert np.isclose(
        data["data"]["magerr"], 2.5 / np.log(10) * corrected_fluxerr / corrected_flux
    )
    assert np.isclose(data["data"]["magref"], -2.5 * np.log10(8.01) + 23.9)
    assert np.isclose(data["data"]["e_magref"], 2.5 / np.log(10) * 0.01 / 8.01)
    assert np.isclose(
        data["data"]["magtot"], -2.5 * np.log10(8.01 + corrected_flux) + 23.9
    )
    total_mag_error_expected = (
        2.5
        / np.log(10)
        * np.sqrt(corrected_fluxerr**2 + 0.01**2)
        / (8.01 + corrected_flux)
    )
    assert np.isclose(data["data"]["e_magtot"], total_mag_error_expected)

    status, data = api(
        "DELETE", f"photometry/{photometry_id}?format=both", token=upload_data_token
    )
    assert_api(status, data)

    # give the reference flux a different zeropoint
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58003.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "ref_flux": 8.01,
            "ref_fluxerr": 0.01,
            "ref_zp": 26.0,  # different zeropoint
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=both", token=upload_data_token
    )
    assert_api(status, data)

    corrected_ref_flux = 8.01 / 10 ** (0.4 * (26.0 - 23.9))
    corrected_ref_fluxerr = 0.01 / 10 ** (0.4 * (26.0 - 23.9))

    assert np.isclose(data["data"]["ref_flux"], corrected_ref_flux)
    assert np.isclose(data["data"]["ref_fluxerr"], corrected_ref_fluxerr)
    assert np.isclose(data["data"]["tot_flux"], corrected_ref_flux + corrected_flux)
    assert np.isclose(
        data["data"]["tot_fluxerr"],
        np.sqrt(corrected_fluxerr**2 + corrected_ref_fluxerr**2),
    )

    # patch the reference flux
    status, data = api(
        "PATCH",
        f"photometry/{photometry_id}",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58003.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "ref_flux": 9.02,
            "ref_fluxerr": 0.03,
            "ref_zp": 27.0,  # same zeropoint
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=both", token=upload_data_token
    )
    assert_api(status, data)
    corrected_ref_flux = 9.02 / 10 ** (0.4 * (27.0 - 23.9))
    corrected_ref_fluxerr = 0.03 / 10 ** (0.4 * (27.0 - 23.9))

    assert np.isclose(data["data"]["ref_flux"], corrected_ref_flux)
    assert np.isclose(data["data"]["ref_fluxerr"], corrected_ref_fluxerr)
    assert np.isclose(data["data"]["tot_flux"], corrected_ref_flux + corrected_flux)
    assert np.isclose(
        data["data"]["tot_fluxerr"],
        np.sqrt(corrected_fluxerr**2 + corrected_ref_fluxerr**2),
    )


def test_ref_mag(upload_data_token, public_source, public_group, ztf_camera):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58003.0,
            "instrument_id": ztf_camera.id,
            "mag": 19.24,
            "limiting_mag": 20.5,
            "magerr": 0.123,
            "magref": 17.01,
            "e_magref": 0.01,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=both", token=upload_data_token
    )
    assert_api(status, data)

    assert data["data"]["altdata"] == {"some_key": "some_value"}

    expected_flux = 10 ** (-0.4 * (19.24 - 23.9))
    expected_fluxerr = 0.123 * (np.log(10) / 2.5) * expected_flux
    assert np.isclose(data["data"]["flux"], expected_flux)
    assert np.isclose(data["data"]["fluxerr"], expected_fluxerr)
    assert np.isclose(data["data"]["mag"], 19.24)
    assert np.isclose(data["data"]["magerr"], 0.123)
    assert np.isclose(data["data"]["magref"], 17.01)
    assert np.isclose(data["data"]["e_magref"], 0.01)

    expected_ref_flux = 10 ** (-0.4 * (17.01 - 23.9))
    expected_ref_fluxerr = 0.01 * (np.log(10) / 2.5) * expected_ref_flux
    assert np.isclose(data["data"]["ref_flux"], expected_ref_flux)
    assert np.isclose(data["data"]["ref_fluxerr"], expected_ref_fluxerr)
    assert np.isclose(data["data"]["tot_flux"], expected_ref_flux + expected_flux)
    assert np.isclose(
        data["data"]["tot_fluxerr"],
        np.sqrt(expected_fluxerr**2 + expected_ref_fluxerr**2),
    )

    assert np.isclose(
        data["data"]["magtot"],
        -2.5 * np.log10(expected_ref_flux + expected_flux) + 23.9,
    )

    expected_mag_error = (
        2.5 / np.log(10) * data["data"]["tot_fluxerr"] / data["data"]["tot_flux"]
    )
    assert np.isclose(data["data"]["e_magtot"], expected_mag_error)

    # patch the reference mag
    status, data = api(
        "PATCH",
        f"photometry/{photometry_id}",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58003.0,
            "instrument_id": ztf_camera.id,
            "mag": 19.24,
            "limiting_mag": 20.5,
            "magerr": 0.123,
            "magref": 18.01,
            "e_magref": 0.02,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=both", token=upload_data_token
    )
    assert_api(status, data)

    expected_ref_flux = 10 ** (-0.4 * (18.01 - 23.9))
    expected_ref_fluxerr = 0.02 * (np.log(10) / 2.5) * expected_ref_flux
    assert np.isclose(data["data"]["ref_flux"], expected_ref_flux)
    assert np.isclose(data["data"]["ref_fluxerr"], expected_ref_fluxerr)
    assert np.isclose(data["data"]["tot_flux"], expected_ref_flux + expected_flux)
    assert np.isclose(
        data["data"]["tot_fluxerr"],
        np.sqrt(expected_fluxerr**2 + expected_ref_fluxerr**2),
    )
    assert np.isclose(data["data"]["magref"], 18.01)
    assert np.isclose(data["data"]["e_magref"], 0.02)


def test_query_magnitudes(upload_data_token, public_source, public_group, ztf_camera):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": public_source.id,
            "instrument_id": ztf_camera.id,
            "mjd": [59410, 59411, 59412],
            "mag": [19.2, 19.3, np.random.uniform(19.3, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "magref": [18.1, 18.2, np.random.uniform(18.2, 19)],
            "e_magref": [0.01, 0.02, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": origin,
            "group_ids": [public_group.id],
            "altdata": {"key1": "value1"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    ids = data["data"]["ids"]
    assert len(ids) == 3

    # check the first point is correct
    status, data = api(
        "GET", f"photometry/{ids[0]}?format=flux", token=upload_data_token
    )
    assert_api(status, data)
    assert data["data"]["magref"] == 18.1
    assert data["data"]["e_magref"] == 0.01
    flux_trans1 = 10 ** (-0.4 * (19.2 - 23.9))
    fluxerr_trans1 = 0.05 / 2.5 * np.log(10) * flux_trans1
    assert np.isclose(data["data"]["flux"], flux_trans1)
    assert np.isclose(data["data"]["fluxerr"], fluxerr_trans1)
    flux_ref1 = 10 ** (-0.4 * (18.1 - 23.9))
    fluxerr_ref1 = 0.01 / 2.5 * np.log(10) * flux_ref1
    assert np.isclose(data["data"]["ref_flux"], flux_ref1)
    assert np.isclose(data["data"]["ref_fluxerr"], fluxerr_ref1)

    assert np.isclose(data["data"]["tot_flux"], flux_trans1 + flux_ref1)
    assert np.isclose(
        data["data"]["tot_fluxerr"],
        np.sqrt(fluxerr_trans1**2 + fluxerr_ref1**2),
    )

    # check the second point is correct
    status, data = api(
        "GET", f"photometry/{ids[1]}?format=flux", token=upload_data_token
    )
    assert_api(status, data)
    assert data["data"]["magref"] == 18.2
    assert data["data"]["e_magref"] == 0.02

    flux_ref2 = 10 ** (-0.4 * (18.2 - 23.9))
    fluxerr_ref2 = 0.02 / 2.5 * np.log(10) * flux_ref2
    assert np.isclose(data["data"]["ref_flux"], flux_ref2)
    assert np.isclose(data["data"]["ref_fluxerr"], fluxerr_ref2)

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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59410, 59411, 59412],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            "group_ids": [public_group.id],
            "altdata": {"key1": "value1"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    ids = data["data"]["ids"]
    assert len(ids) == 3

    for id in ids:
        status, data = api(
            "GET", f"photometry/{id}?format=flux", token=upload_data_token
        )
        assert status == 200
        assert data["status"] == "success"
        assert data["data"]["altdata"] == {"key1": "value1"}


def test_post_multiple_photometry_vector_altdata(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59408, 59409, 59410],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            "group_ids": [public_group.id],
            "altdata": [{"key1": "value1"}, {"key2": "value2"}, {"key3": "value3"}],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    ids = data["data"]["ids"]
    assert len(ids) == 3

    keys = []
    values = []
    for id in ids:
        status, data = api(
            "GET", f"photometry/{id}?format=flux", token=upload_data_token
        )
        assert status == 200
        assert data["status"] == "success"
        assert data["data"]["altdata"] in [
            {"key1": "value1"},
            {"key2": "value2"},
            {"key3": "value3"},
        ]
        keys.append(list(data["data"]["altdata"].keys())[0])
        values.append(list(data["data"]["altdata"].values())[0])
    # Ensure each phot record was assigned associated distinct aldata value
    assert sorted(keys) == ["key1", "key2", "key3"]
    assert sorted(values) == ["value1", "value2", "value3"]


def test_post_multiple_photometry_scalar_altdata(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59410, 59411, 59412],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            "group_ids": [public_group.id],
            "altdata": {"key1": "value1"},
        },
        token=upload_data_token,
    )
    assert_api(status, data)

    ids = data["data"]["ids"]
    assert len(ids) == 3

    for id in ids:
        status, data = api(
            "GET", f"photometry/{id}?format=flux", token=upload_data_token
        )
        assert status == 200
        assert data["status"] == "success"
        assert data["data"]["altdata"] == {"key1": "value1"}


def test_token_user_post_put_photometry_data(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    ids = data["data"]["ids"]
    assert len(ids) == 3

    # POSTing photometry that contains the same first two points should fail:
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"

    # PUTing photometry that contains
    # the same first point, the second point with a different origin, and a new third point should succeed
    # only the last two points will be ingested
    status, data = api(
        "PUT",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "omg", "lol"],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_ids = data["data"]["ids"]
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
    input_data = {
        "obj_id": str(public_source.id),
        "instrument_id": ztf_camera.id,
        "mjd": [59400, 59401, 59403],
        "mag": [20.2, 20.3, np.random.uniform(18, 19)],
        "magerr": [0.05, 0.1, np.random.uniform(0.01, 0.1)],
        "limiting_mag": [21.0, 20.1, 20.2],
        "magsys": ["ab", "ab", "ab"],
        "filter": ["ztfr", "ztfg", "ztfr"],
        "ra": [42.01, 42.01, 42.02],
        "dec": [42.02, 42.01, 42.03],
        "origin": [None, "omg", "lol"],
        "group_ids": [public_group.id],
    }

    # this feature is reserved to super admin, so this should fail
    status, data = api(
        "PUT",
        "photometry?duplicate_ignore_flux=True&overwrite_flux=True",
        data=input_data,
        token=upload_data_token,
    )
    assert status == 400
    assert (
        "Ignoring flux/fluxerr when checking for duplicates is reserved to super admin users only"
        in data["message"]
    )

    # try with the super admin token now
    status, data = api(
        "PUT",
        "photometry?duplicate_ignore_flux=True&overwrite_flux=True",
        data=input_data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    new_ids = data["data"]["ids"]
    assert len(new_ids) == 3
    # we should have 1 same + 1 updated - 1 new = 2 identical ids
    assert len(set(new_ids).intersection(set(ids))) == 2

    # GET the photometry
    # First point should be identical
    status, data = api(
        "GET", f"photometry/{ids[0]}?format=mag", token=upload_data_token
    )
    assert status == 200
    assert "data" in data
    data = data["data"]
    assert data["mjd"] == 59400
    assert data["mag"] == 19.2
    assert data["magerr"] == 0.05

    # second point should be updated
    status, data = api(
        "GET", f"photometry/{ids[1]}?format=mag", token=upload_data_token
    )
    assert status == 200
    assert "data" in data
    data = data["data"]
    assert data["mjd"] == 59401
    assert data["mag"] == 20.3
    assert data["magerr"] == 0.1


def test_token_user_post_put_get_photometry_data(
    upload_data_token_two_groups, public_source, public_group, public_group2, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59400, 59401, 59402],
            "mag": [19.2, 19.3, np.random.uniform(19, 20)],
            "magerr": [0.05, 0.06, np.random.uniform(0.01, 0.1)],
            "limiting_mag": [20.0, 20.1, 20.2],
            "magsys": ["ab", "ab", "ab"],
            "filter": ["ztfr", "ztfg", "ztfr"],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "origin": [None, "lol", "lol"],
            "group_ids": [public_group.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"
    ids = data["data"]["ids"]
    assert len(ids) == 3

    status, data = api(
        "GET", f"photometry/{ids[0]}?format=flux", token=upload_data_token_two_groups
    )
    assert status == 200
    assert data["status"] == "success"
    group_ids = [g["id"] for g in data["data"]["groups"]]
    assert len(group_ids) == 2
    assert public_group.id in group_ids

    # PUTing photometry that contains
    # the same first point, the second point with a different origin, and a new third point should succeed
    # only the last two points will be ingested
    status, data = api(
        "PUT",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "instrument_id": ztf_camera.id,
            "mjd": [59400, 59401],
            "mag": [19.2, 19.3],
            "magerr": [0.05, 0.06],
            "limiting_mag": [20.0, 20.1],
            "magsys": ["ab", "ab"],
            "filter": ["ztfr", "ztfg"],
            "ra": [42.01, 42.01],
            "dec": [42.02, 42.01],
            "origin": [None, "lol"],
            "group_ids": [public_group.id, public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"
    new_ids = data["data"]["ids"]
    assert len(new_ids) == 2
    assert len(set(new_ids).intersection(set(ids))) == 2

    status, data = api(
        "GET", f"photometry/{ids[0]}?format=flux", token=upload_data_token_two_groups
    )
    assert status == 200
    assert data["status"] == "success"
    group_ids = [g["id"] for g in data["data"]["groups"]]
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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id, public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["ra"] is None
    assert data["data"]["dec"] is None
    assert data["data"]["ra_unc"] is None
    assert data["data"]["dec_unc"] is None

    assert len(data["data"]["groups"]) == 3

    np.testing.assert_allclose(
        data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": "all",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET",
        f"photometry/{photometry_id}?format=flux",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["ra"] is None
    assert data["data"]["dec"] is None
    assert data["data"]["ra_unc"] is None
    assert data["data"]["dec_unc"] is None

    # Groups should be single user group and public group
    assert len(data["data"]["groups"]) == 2
    groups = [g["name"] for g in data["data"]["groups"]]
    assert cfg["misc"]["public_group_name"] in groups
    assert user_two_groups.single_user_group.name in groups

    np.testing.assert_allclose(
        data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id, public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["ra"] is None
    assert data["data"]["dec"] is None
    assert data["data"]["ra_unc"] is None
    assert data["data"]["dec_unc"] is None

    np.testing.assert_allclose(
        data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25.0 - 23.9))
    )


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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group2.id],
        },
        token=upload_data_token,
    )
    # the upload_data_token user's single user group id is =
    # Token.query.get(upload_data_token).created_by.single_user_group.id

    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )

    # the view-only token group ids =
    # [g.id for g in Token.query.get(view_only_token).created_by.groups]

    # `view_only_token only` belongs to `public_group`, not `public_group2`
    assert status == 400
    assert data["status"] == "error"
    assert "Cannot find photometry point with ID" in data["message"]


def test_can_post_photometry_no_groups(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 1


def test_can_post_photometry_empty_groups_list(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [],
        },
        token=upload_data_token,
    )

    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["groups"]) == 1


def test_token_user_post_mag_photometry_data_and_convert(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": 21.0,
            "magerr": 0.2,
            "limiting_mag": 22.3,
            "magsys": "vega",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    correction = 2.5 * np.log10(vega.zpbandflux("ztfg") / ab.zpbandflux("ztfg"))

    np.testing.assert_allclose(
        data["data"]["flux"], 10 ** (-0.4 * (21.0 - correction - 23.9))
    )

    np.testing.assert_allclose(
        data["data"]["fluxerr"], 0.2 / (2.5 / np.log(10)) * data["data"]["flux"]
    )

    status, data = api("GET", f"photometry/{photometry_id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    np.testing.assert_allclose(data["data"]["mag"], 21.0 - correction)

    np.testing.assert_allclose(data["data"]["magerr"], 0.2)


def test_token_user_post_and_get_different_systems_mag(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": 21.0,
            "magerr": 0.2,
            "limiting_mag": 22.3,
            "magsys": "vega",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET",
        f"photometry/{photometry_id}?format=mag&magsys=vega",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["magsys"] == "vega"

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    correction = 2.5 * np.log10(vega.zpbandflux("ztfg") / ab.zpbandflux("ztfg"))

    np.testing.assert_allclose(data["data"]["mag"], 21.0)
    np.testing.assert_allclose(data["data"]["magerr"], 0.2)
    np.testing.assert_allclose(data["data"]["limiting_mag"], 22.3)

    status, data = api(
        "GET",
        f"photometry/{photometry_id}?format=mag&magsys=ab",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    np.testing.assert_allclose(data["data"]["mag"], 21.0 - correction)
    np.testing.assert_allclose(data["data"]["magerr"], 0.2)
    np.testing.assert_allclose(data["data"]["limiting_mag"], 22.3 - correction)


def test_token_user_post_and_get_different_systems_flux(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": 21.0,
            "magerr": 0.2,
            "limiting_mag": 22.3,
            "magsys": "vega",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET",
        f"photometry/{photometry_id}?format=flux&magsys=vega",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    correction = 2.5 * np.log10(vega.zpbandflux("ztfg") / ab.zpbandflux("ztfg"))

    np.testing.assert_allclose(
        data["data"]["flux"], 10 ** (-0.4 * (21 - correction - 23.9))
    )
    np.testing.assert_allclose(
        data["data"]["fluxerr"], 0.2 / (2.5 / np.log(10)) * data["data"]["flux"]
    )
    np.testing.assert_allclose(data["data"]["zp"], 23.9 + correction)

    status, data = api(
        "GET",
        f"photometry/{photometry_id}?format=flux&magsys=ab",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    np.testing.assert_allclose(
        data["data"]["flux"], 10 ** (-0.4 * (21 - correction - 23.9))
    )
    np.testing.assert_allclose(
        data["data"]["fluxerr"], 0.2 / (2.5 / np.log(10)) * data["data"]["flux"]
    )
    np.testing.assert_allclose(data["data"]["zp"], 23.9)


def test_token_user_mixed_photometry_post(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": 21.0,
            "magerr": [0.2, 0.1],
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][1]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    np.testing.assert_allclose(data["data"]["flux"], 10 ** (-0.4 * (21.0 - 23.9)))

    np.testing.assert_allclose(
        data["data"]["fluxerr"], 0.1 / (2.5 / np.log(10)) * data["data"]["flux"]
    )

    # should fail as len(mag) != len(magerr)
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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    if status != 200:
        print(data)
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["flux"] is None
    np.testing.assert_allclose(
        data["data"]["fluxerr"], 10 ** (-0.4 * (22.3 - 23.9)) / PHOT_DETECTION_THRESHOLD
    )

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": None,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    assert data["data"]["flux"] is None
    np.testing.assert_allclose(
        data["data"]["fluxerr"], 0.031 * 10 ** (-0.4 * (25.0 - 23.9))
    )


def test_token_user_post_invalid_filter(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "bessellv",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_token_user_post_photometry_data_series(
    upload_data_token, public_source, ztf_camera, public_group
):
    # valid request
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000.0, 58001.0, 58002.0],
            "instrument_id": ztf_camera.id,
            "flux": [12.24, 15.24, 12.24],
            "fluxerr": [0.031, 0.029, 0.030],
            "filter": ["ztfg", "ztfg", "ztfg"],
            "zp": [25.0, 30.0, 21.2],
            "magsys": ["ab", "ab", "ab"],
            "ra": 264.1947917,
            "dec": [50.5478333, 50.5478333 + 0.00001, 50.5478333],
            "dec_unc": 0.2,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == 3

    photometry_id = data["data"]["ids"][1]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert np.allclose(data["data"]["flux"], 15.24 * 10 ** (-0.4 * (30 - 23.9)))

    assert np.allclose(data["data"]["dec"], 50.5478333 + 0.00001)

    assert np.allclose(data["data"]["dec_unc"], 0.2)
    assert data["data"]["ra_unc"] is None

    # invalid request
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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"


def test_token_user_update_photometry(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
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
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    np.testing.assert_allclose(data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api(
        "PATCH",
        f"photometry/{photometry_id}",
        data={
            "obj_id": str(public_source.id),
            "flux": 11.0,
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfi",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    np.testing.assert_allclose(data["data"]["flux"], 11.0 * 10 ** (-0.4 * (25 - 23.9)))


def test_token_user_cannot_update_unowned_photometry(
    upload_data_token, manage_sources_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
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
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    np.testing.assert_allclose(data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api(
        "PATCH",
        f"photometry/{photometry_id}",
        data={
            "obj_id": str(public_source.id),
            "flux": 11.0,
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfi",
        },
        token=manage_sources_token,
    )
    assert status == 401


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

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfi",
            "group_ids": [public_group.id, public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "PATCH",
        f"photometry/{photometry_id}",
        data={
            "obj_id": str(public_source.id),
            "flux": 11.0,
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfi",
            "group_ids": [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=view_only_token
    )
    assert status == 400
    assert data["status"] == "error"
    assert "Cannot find photometry point with ID" in data["message"]


def test_user_can_delete_owned_photometry_data(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
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
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    np.testing.assert_allclose(data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api("DELETE", f"photometry/{photometry_id}", token=upload_data_token)
    assert status == 200

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 400


def test_user_cannot_delete_unowned_photometry_data(
    upload_data_token, manage_sources_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
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
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    np.testing.assert_allclose(data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api(
        "DELETE", f"photometry/{photometry_id}", token=manage_sources_token
    )

    assert status == 401


def test_admin_can_delete_unowned_photometry_data(
    upload_data_token, super_admin_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
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
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    np.testing.assert_allclose(data["data"]["flux"], 12.24 * 10 ** (-0.4 * (25 - 23.9)))

    status, data = api("DELETE", f"photometry/{photometry_id}", token=super_admin_token)
    assert status == 200

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 400


def test_token_user_retrieving_source_photometry_and_convert(
    view_only_token, public_source
):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry?format=flux&magsys=ab",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    assert "mjd" in data["data"][0]
    assert "ra_unc" in data["data"][0]

    data["data"] = sorted(data["data"], key=lambda d: d["mjd"])
    mag1_ab = -2.5 * np.log10(data["data"][0]["flux"]) + data["data"][0]["zp"]
    magerr1_ab = 2.5 / np.log(10) * data["data"][0]["fluxerr"] / data["data"][0]["flux"]

    maglast_ab = -2.5 * np.log10(data["data"][-1]["flux"]) + data["data"][-1]["zp"]
    magerrlast_ab = (
        2.5 / np.log(10) * data["data"][-1]["fluxerr"] / data["data"][-1]["flux"]
    )

    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry?format=mag&magsys=ab",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"

    data["data"] = sorted(data["data"], key=lambda d: d["mjd"])
    assert np.allclose(mag1_ab, data["data"][0]["mag"])
    assert np.allclose(magerr1_ab, data["data"][0]["magerr"])

    assert np.allclose(maglast_ab, data["data"][-1]["mag"])
    assert np.allclose(magerrlast_ab, data["data"][-1]["magerr"])

    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry?format=flux&magsys=vega",
        token=view_only_token,
    )

    data["data"] = sorted(data["data"], key=lambda d: d["mjd"])
    mag1_vega = -2.5 * np.log10(data["data"][0]["flux"]) + data["data"][0]["zp"]
    magerr1_vega = (
        2.5 / np.log(10) * data["data"][0]["fluxerr"] / data["data"][0]["flux"]
    )

    maglast_vega = -2.5 * np.log10(data["data"][-1]["flux"]) + data["data"][-1]["zp"]
    magerrlast_vega = (
        2.5 / np.log(10) * data["data"][-1]["fluxerr"] / data["data"][-1]["flux"]
    )

    assert status == 200
    assert data["status"] == "success"

    ab = sncosmo.get_magsystem("ab")
    vega = sncosmo.get_magsystem("vega")
    vega_to_ab = {
        filter: 2.5 * np.log10(ab.zpbandflux(filter) / vega.zpbandflux(filter))
        for filter in ["ztfg", "ztfr", "ztfi"]
    }

    assert np.allclose(mag1_ab, mag1_vega + vega_to_ab[data["data"][0]["filter"]])
    assert np.allclose(magerr1_ab, magerr1_vega)

    assert np.allclose(
        maglast_ab, maglast_vega + vega_to_ab[data["data"][-1]["filter"]]
    )
    assert np.allclose(magerrlast_ab, magerrlast_vega)


def test_token_user_retrieve_null_photometry(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["flux"] is None

    np.testing.assert_allclose(
        data["data"]["fluxerr"], 10 ** (-0.4 * (22.3 - 23.9)) / PHOT_DETECTION_THRESHOLD
    )

    status, data = api(
        "GET", f"photometry/{photometry_id}?format=mag", token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["mag"] is None
    assert data["data"]["magerr"] is None


def test_token_user_get_range_photometry(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000.0, 58500.0, 59000.0],
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        "photometry/range",
        token=upload_data_token,
        data={"instrument_ids": [ztf_camera.id], "max_date": "2018-05-15T00:00:00"},
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1

    status, data = api(
        "GET",
        "photometry/range?format=flux&magsys=vega",
        token=upload_data_token,
        data={"instrument_ids": [ztf_camera.id], "max_date": "2019-02-01T00:00:00"},
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 2


def test_token_user_post_to_foreign_group_and_retrieve(
    upload_data_token, public_source_two_groups, public_group2, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source_two_groups.id),
            "mjd": [58000.0, 58500.0, 59000.0],
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group2.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    photometry_id = data["data"]["ids"][0]
    status, data = api(
        "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
    )
    assert status == 200


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

    status, data = api(
        "POST",
        "photometry",
        data=payload,
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

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

    status, data = api(
        "POST",
        "photometry",
        data=payload,
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    payload["group_ids"] = "all"

    status, data = api(
        "PUT",
        "photometry",
        data=payload,
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    for id in data["data"]["ids"]:
        status, data = api(
            "GET", f"photometry/{id}?format=flux", token=upload_data_token
        )
        assert status == 200
        assert data["status"] == "success"
        assert len(data["data"]["groups"]) == 2


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

    status, data = api(
        "PUT",
        "photometry",
        data=payload,
        token=super_admin_token,
    )
    assert status in [400, 500]
    assert data["status"] == "error"


def test_cannot_post_negative_fluxerr(
    upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": -0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "Invalid value" in data["message"]

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000.0, 58000.4],
            "instrument_id": ztf_camera.id,
            "flux": [12.24, 12.43],
            "fluxerr": [0.35, -0.031],
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert "Invalid value" in data["message"]


def test_photometry_stream_read_access(
    upload_data_token,
    view_only_token_no_groups,
    view_only_token_no_groups_no_streams,
    public_source,
    public_stream,
    ztf_camera,
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    photometry_id = data["data"]["ids"][0]

    # this token has sufficient stream access
    status, data = api(
        "GET", f"photometry/{photometry_id}", token=view_only_token_no_groups
    )
    assert status == 200
    assert data["status"] == "success"

    # this token does not have sufficient stream access
    status, data = api(
        "GET", f"photometry/{photometry_id}", token=view_only_token_no_groups_no_streams
    )
    assert status == 400
    assert data["status"] == "error"


def test_photometry_stream_post_access(
    upload_data_token_no_groups,
    upload_data_token_no_groups_no_streams,
    public_source,
    public_stream,
    ztf_camera,
):
    # this token has sufficient stream access to create a StreamPhotometry row
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups,
    )
    assert status == 200
    assert data["status"] == "success"

    # this token doesn't have sufficient stream access to create a StreamPhotometry row
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups_no_streams,
    )
    assert status == 400
    assert data["status"] == "error"


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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups,
    )
    assert status == 200
    assert data["status"] == "success"

    # this token doesn't have sufficient stream access to add to stream2
    status, data = api(
        "PUT",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream2.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups_no_streams,
    )
    assert status == 400
    assert data["status"] == "error"

    # this token doesn't have sufficient stream access to create a StreamPhotometry row
    status, data = api(
        "PUT",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream2.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups,
    )
    assert status == 400
    assert data["status"] == "error"

    # this token does have sufficient stream access to add to stream2
    status, data = api(
        "PUT",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream2.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_stream2,
    )
    assert status == 200
    assert data["status"] == "success"


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
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups_two_streams,
    )
    assert status == 200
    assert data["status"] == "success"
    phot_id = data["data"]["ids"][0]

    # this token doesn't have sufficient stream access to add to stream2
    status, data = api(
        "PATCH",
        f"photometry/{phot_id}",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream2.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups_no_streams,
    )
    assert status == 400
    assert data["status"] == "error"

    # this token doesn't have sufficient stream access to create a StreamPhotometry row
    status, data = api(
        "PATCH",
        f"photometry/{phot_id}",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream2.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups,
    )
    assert status == 400
    assert data["status"] == "error"

    # this token does have sufficient stream access to add to stream2
    status, data = api(
        "PATCH",
        f"photometry/{phot_id}",
        data={
            "obj_id": str(public_source.id),
            "mjd": 58001.0,
            "instrument_id": ztf_camera.id,
            "flux": 13.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "stream_ids": [public_stream2.id],
            "altdata": {"some_key": "some_value"},
        },
        token=upload_data_token_no_groups_two_streams,
    )
    assert status == 200
    assert data["status"] == "success"


def test_token_user_delete_object_photometry(
    super_admin_token, upload_data_token, view_only_token, ztf_camera, public_group
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) > 0

    status, data = api(
        "DELETE",
        f"sources/{obj_id}/photometry",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 0


def test_photometry_validation(
    super_admin_token, upload_data_token, view_only_token, ztf_camera, public_group
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 58000.0,
            "instrument_id": ztf_camera.id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    photometry_id = data["data"]["ids"][0]

    # insufficient access, should fail
    status, data = api(
        "POST",
        f"photometry/{photometry_id}/validation",
        data={
            "validated": True,
            "explanation": "GOOD SUBTRACTION",
            "notes": "beautiful image",
        },
        token=view_only_token,
    )
    assert status == 401
    assert data["status"] == "error"

    status, data = api(
        "POST",
        f"photometry/{photometry_id}/validation",
        data={
            "validated": True,
            "explanation": "GOOD SUBTRACTION",
            "notes": "beautiful image",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=view_only_token,
        params={"includeValidationInfo": True},
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) > 0
    assert len(data["data"][0]["validations"]) > 0
    assert data["data"][0]["validations"][0]["explanation"] == "GOOD SUBTRACTION"
    assert data["data"][0]["validations"][0]["notes"] == "beautiful image"
    assert data["data"][0]["validations"][0]["validated"] is True

    status, data = api(
        "PATCH",
        f"photometry/{photometry_id}/validation",
        data={
            "validated": False,
            "explanation": "BAD SUBTRACTION",
            "notes": "ugly image",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=view_only_token,
        params={"includeValidationInfo": True},
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) > 0
    assert len(data["data"][0]["validations"]) > 0
    assert data["data"][0]["validations"][0]["explanation"] == "BAD SUBTRACTION"
    assert data["data"][0]["validations"][0]["notes"] == "ugly image"
    assert data["data"][0]["validations"][0]["validated"] is False

    status, data = api(
        "DELETE",
        f"photometry/{photometry_id}/validation",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=view_only_token,
        params={"includeValidationInfo": True},
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) > 0
    assert len(data["data"][0]["validations"]) == 0


def test_post_external_photometry(
    upload_data_token, super_admin_token, super_admin_user, public_group
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["atlaso", "atlasc"],
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    datafile = f"{os.path.dirname(__file__)}/../../data/ZTFrlh6cyjh_ATLAS.csv"
    df = pd.read_csv(datafile)
    df.drop(columns=["index"], inplace=True)

    data_out = {
        "obj_id": obj_id,
        "instrument_id": instrument_id,
        "group_ids": "all",
        **df.to_dict(orient="list"),
    }

    add_external_photometry(data_out, super_admin_user)

    # Check the photometry sent back with the source
    status, data = api(
        "GET",
        f"sources/{obj_id}",
        params={"includePhotometry": "true"},
        token=super_admin_token,
    )
    assert status == 200
    assert len(data["data"]["photometry"]) == 384

    assert all(p["obj_id"] == obj_id for p in data["data"]["photometry"])
    assert all(p["instrument_id"] == instrument_id for p in data["data"]["photometry"])


def test_token_user_big_post(
    upload_data_token, public_source, ztf_camera, public_group
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000 + i for i in range(30000)],
            "instrument_id": ztf_camera.id,
            "mag": np.random.uniform(low=18, high=22, size=30000).tolist(),
            "magerr": np.random.uniform(low=0.1, high=0.3, size=30000).tolist(),
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert (
        data["message"]
        == "Maximum number of photometry rows to post exceeded: 30000 > 10000. Please break up the data into smaller sets and try again"
    )
