"""Provider-level tests for broker_apis.

Two complementary mechanisms give every broker deterministic coverage without a
live network:

* REST brokers (ALeRCE, Fink, ANTARES, Lasair, ...) — HTTP replayed from vcrpy
  cassettes under ``data/broker_cassettes/`` (recorded live, credentials filtered
  out). To (re)record: delete the cassette and run with ``record_mode="once"``
  against the live API from a networked host, then commit it. Client-backed
  brokers (ANTARES/Lasair) ``importorskip`` their client so CI without it skips.
* Kafka/BigQuery brokers (AMPEL, Babamul, Pitt-Google) — vcr can't record those
  transports, so a real payload is saved instead: a live Kafka Avro message
  (``*.avro``) or a live BigQuery result (``*.json``), replayed through the
  broker's decode/normalize. (BOOM's interactive path is REST, so it gets a true
  cassette.) Normalization edge cases are additionally unit-tested.

Every broker thus has a deterministic test backed by real recorded data.
"""

import json
import os

import fastavro
import pytest
import vcr

from skyportal.broker_apis.alerce import ALERCEBROKER, _normalize_object
from skyportal.broker_apis.ampel import _normalize_ampel_report
from skyportal.broker_apis.antares import _normalize_locus
from skyportal.broker_apis.boom import BOOMBROKER, _normalize_boom_alert
from skyportal.broker_apis.fink import (
    FINKBROKER,
    _fink_survey,
    _normalize_fink_lsst,
    _normalize_fink_object,
)
from skyportal.broker_apis.lasair import _normalize_object as _normalize_lasair
from skyportal.broker_apis.pittgoogle import _normalize_pubsub_alert, _normalize_rows

CASSETTE_DIR = os.path.join(os.path.dirname(__file__), "data", "broker_cassettes")

# Replay only (never touch the network in CI); a missing/stale cassette fails.
broker_vcr = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["method", "scheme", "host", "path", "query", "body"],
)

# BOOM's /auth request body has its credentials filtered out, so match by path
# only (its two requests — /auth and /queries/cone_search — are path-distinct).
boom_vcr = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["method", "scheme", "host", "path"],
)


class _MockBroker:
    """Minimal stand-in for a Broker row (providers only read ``altdata``)."""

    def __init__(self, altdata):
        self.altdata = altdata


def _assert_standard_shape(data):
    assert "objectId" in data and data["objectId"]
    assert "candidate" in data and "ra" in data["candidate"]
    assert isinstance(data["prv_candidates"], list)


# --- REST brokers: replayed from recorded HTTP -------------------------------


def test_alerce_get_alert_cassette():
    broker = _MockBroker({"survey": "ZTF"})
    with broker_vcr.use_cassette("alerce_get_alert.yaml"):
        data = ALERCEBROKER.get_alert(broker, "ZTF18abcgqmz", None)
    _assert_standard_shape(data)
    assert data["objectId"] == "ZTF18abcgqmz"
    assert data["candidate"]["magpsf"] is not None
    assert all(p["band"] in ("g", "r", "i") for p in data["prv_candidates"])


def test_alerce_lsst_get_alert_cassette():
    # ALeRCE LSST is the flux-space multisurvey API (distinct host + schema).
    broker = _MockBroker({"survey": "LSST"})
    with broker_vcr.use_cassette("alerce_lsst_get_alert.yaml"):
        data = ALERCEBROKER.get_alert(broker, "170587116732416143", None)
    _assert_standard_shape(data)
    assert data["objectId"] == "170587116732416143"
    assert data["candidate"]["psfFlux"] is not None
    assert all(p["psfFlux"] is not None for p in data["prv_candidates"])
    assert all(
        p["band"] in ("u", "g", "r", "i", "z", "y") for p in data["prv_candidates"]
    )


def test_fink_get_alert_cassette():
    broker = _MockBroker({"survey": "ZTF"})
    with broker_vcr.use_cassette("fink_get_alert.yaml"):
        data = FINKBROKER.get_alert(broker, "ZTF19aaosfcb", None)
    _assert_standard_shape(data)
    assert data["objectId"] == "ZTF19aaosfcb"
    assert len(data["prv_candidates"]) >= 1


def test_antares_get_alert_cassette():
    pytest.importorskip("antares_client")
    from skyportal.broker_apis.antares import ANTARESBROKER

    broker = _MockBroker({"survey": "ZTF"})
    with broker_vcr.use_cassette("antares_get_alert.yaml"):
        data = ANTARESBROKER.get_alert(broker, "ZTF26abeuijw", None)
    _assert_standard_shape(data)
    assert data["objectId"] == "ZTF26abeuijw"


def test_lasair_cone_cassette():
    pytest.importorskip("lasair")
    from skyportal.broker_apis.lasair import LASAIRBROKER

    broker = _MockBroker(
        {"survey": "ZTF", "token": "x", "endpoint": "https://lasair-ztf.lsst.ac.uk/api"}
    )
    with broker_vcr.use_cassette("lasair_cone.yaml"):
        rows = LASAIRBROKER.cone_search(broker, 280.0, -5.0, 600, None)
    assert rows is not None
    assert len(rows) >= 1


def test_boom_query_cassette():
    broker = _MockBroker(
        {
            "protocol": "https",
            "host": "api.kaboom.caltech.edu",
            "username": "x",
            "password": "y",
        }
    )
    with boom_vcr.use_cassette("boom_query.yaml"):
        # auth (/auth) + /queries/cone_search are replayed; the bearer token in
        # the recorded /auth response is scrubbed.
        results = BOOMBROKER.query_alerts(
            broker, None, ra=280.0, dec=-5.0, radius=5, radius_units="arcsec"
        )
    assert isinstance(results, list)


# --- Real recorded payloads: Kafka Avro + BigQuery fixtures -------------------


def test_ampel_report_fixture():
    with open(os.path.join(CASSETTE_DIR, "ampel_report.avro"), "rb") as f:
        report = next(iter(fastavro.reader(f)))
    data, candid = _normalize_ampel_report(report)
    _assert_standard_shape(data)
    assert data["prv_candidates"]  # real report carries photometry
    assert all(p["psfFluxErr"] is not None for p in data["prv_candidates"])


def test_pittgoogle_rows_fixture():
    with open(os.path.join(CASSETTE_DIR, "pittgoogle_rows.json")) as f:
        fx = json.load(f)
    data = _normalize_rows(fx["objectId"], fx["rows"])
    _assert_standard_shape(data)
    assert data["objectId"] == "ZTF19acfixfe"
    assert len(data["prv_candidates"]) >= 1


def test_babamul_alert_fixture():
    # babamul passes the raw ZTF Avro alert straight to the shared save; assert
    # the recorded message decodes to the expected alert shape.
    with open(os.path.join(CASSETTE_DIR, "babamul_alert.avro"), "rb") as f:
        alert = next(iter(fastavro.reader(f)))
    assert alert.get("objectId")
    assert "prv_candidates" in alert or "candidate" in alert


# --- Normalization units (transport-agnostic core) ---------------------------


def test_alerce_normalize():
    dets = [
        {
            "mjd": 58847.0,
            "magpsf": 19.1,
            "sigmapsf": 0.19,
            "fid": 2,
            "ra": 15.0,
            "dec": -21.0,
            "candid": 1,
        },
        {
            "mjd": 58850.0,
            "magpsf": 18.6,
            "sigmapsf": 0.10,
            "fid": 1,
            "ra": 15.0,
            "dec": -21.0,
            "candid": 2,
        },
    ]
    d = _normalize_object("ZTF19a", {"meanra": 15.0, "meandec": -21.0}, dets)
    _assert_standard_shape(d)
    assert d["candidate"]["band"] == "g"  # latest detection is fid=1
    assert len(d["prv_candidates"]) == 2


def test_fink_ztf_normalize():
    rows = [
        {
            "i:objectId": "ZTF1",
            "i:jd": 2458700.5,
            "i:magpsf": 18.9,
            "i:sigmapsf": 0.1,
            "i:fid": 1,
            "i:ra": 1.0,
            "i:dec": 2.0,
        },
        {
            "i:objectId": "ZTF1",
            "i:jd": 2458702.5,
            "i:magpsf": 18.4,
            "i:sigmapsf": 0.1,
            "i:fid": 2,
            "i:ra": 1.0,
            "i:dec": 2.0,
        },
    ]
    d = _normalize_fink_object("ZTF1", rows)
    _assert_standard_shape(d)
    assert [p["band"] for p in d["prv_candidates"]] == ["g", "r"]


def test_fink_lsst_normalize():
    rows = [
        {
            "r:midpointMjdTai": 60500.1,
            "r:psfFlux": 2400.0,
            "r:psfFluxErr": 380.0,
            "r:band": "g",
            "r:ra": 55.8,
            "r:dec": -32.4,
        },
        {
            "r:midpointMjdTai": 60505.2,
            "r:psfFlux": 3100.0,
            "r:psfFluxErr": 300.0,
            "r:band": "r",
            "r:ra": 55.8,
            "r:dec": -32.4,
        },
    ]
    d = _normalize_fink_lsst("312423", rows)
    _assert_standard_shape(d)
    assert d["prv_candidates"][-1]["psfFlux"] == 3100.0  # flux space
    assert d["candidate"]["band"] == "r"


def test_antares_normalize():
    class _Alert:
        def __init__(self, mjd, mag, fid):
            self.mjd = mjd
            self.alert_id = "ztf_candidate:1"
            self.properties = {
                "ant_mjd": mjd,
                "ant_mag": mag,
                "ant_magerr": 0.1,
                "ztf_fid": fid,
                "ant_ra": 10.1,
                "ant_dec": 20.2,
            }

    class _Locus:
        ra = 10.1
        dec = 20.2
        locus_id = "ANT1"
        properties = {"ztf_object_id": "ZTF19x"}
        alerts = [_Alert(58847.0, 19.1, 2), _Alert(58850.0, 18.6, 1)]

    d = _normalize_locus(_Locus())
    _assert_standard_shape(d)
    assert d["objectId"] == "ZTF19x"
    assert [p["band"] for p in d["prv_candidates"]] == ["r", "g"]  # sorted by jd


def test_lasair_normalize():
    obj = {
        "objectId": "ZTFlasair",
        "objectData": {"ramean": 150.2, "decmean": 2.3},
        "candidates": [
            {
                "magpsf": 18.5,
                "sigmapsf": 0.1,
                "jd": 2459000.5,
                "fid": 1,
                "ra": 150.2,
                "dec": 2.3,
            }
        ],
    }
    d = _normalize_lasair(obj, "ZTFlasair")
    _assert_standard_shape(d)
    assert d["prv_candidates"][0]["magpsf"] == 18.5


def test_boom_normalize_skips_sentinel():
    rec = {
        "objectId": "BOOM1",
        "candid": 7,
        "survey": "ZTF",
        "ra": 1.0,
        "dec": 2.0,
        "photometry": [
            {
                "flux": 500.0,
                "flux_err": 50.0,
                "jd": 2459000.5,
                "band": "g",
                "programid": 1,
            },
            {
                "flux": -99999.0,
                "flux_err": -99999.0,
                "jd": 2459001.5,
                "band": "r",
                "programid": 1,
            },
        ],
    }
    d = _normalize_boom_alert(rec)
    _assert_standard_shape(d)
    assert len(d["prv_candidates"]) == 1  # the -99999 sentinel point is dropped
    assert d["prv_candidates"][0]["psfFlux"] == 500.0


def test_pittgoogle_normalize_bigquery_rows():
    rows = [
        {
            "jd": 2458847.0,
            "fid": 2,
            "magpsf": 19.1,
            "sigmapsf": 0.19,
            "ra": 10.1,
            "decl": 20.2,
        },
        {
            "jd": 2458850.0,
            "fid": 1,
            "magpsf": 18.6,
            "sigmapsf": 0.10,
            "ra": 10.1,
            "decl": 20.2,
        },
    ]
    d = _normalize_rows("ZTFbq", rows)
    _assert_standard_shape(d)
    assert d["candidate"]["dec"] == 20.2
    assert d["candidate"]["band"] == "g"


def test_pittgoogle_normalize_pubsub_alert():
    class _Alert:
        dict = {
            "objectId": "ZTFps",
            "candidate": {
                "jd": 2460288.6,
                "fid": 1,
                "magpsf": 18.1,
                "sigmapsf": 0.1,
                "ra": 322.9,
                "dec": 49.2,
                "candid": 99,
            },
            "prv_candidates": [
                {
                    "jd": 2460284.6,
                    "fid": 2,
                    "magpsf": 18.5,
                    "sigmapsf": 0.1,
                    "ra": 322.9,
                    "dec": 49.2,
                }
            ],
            "cutoutScience": {"stampData": b"fits"},
        }

    data, candid, cutouts = _normalize_pubsub_alert(_Alert())
    _assert_standard_shape(data)
    assert candid == 99
    assert cutouts and "cutoutScience" in cutouts


def test_ampel_normalize_report():
    report = {
        "object": {
            "id": 170463893335834628,
            "ra": 149.7,
            "dec": 1.46,
            "source": "LSST",
        },
        "photometry": [
            {
                "time": 2461189.5,
                "flux": 6053.6,
                "fluxerr": 403.4,
                "band": "lssti",
                "zp": 31.4,
                "zpsys": "ab",
            },
            {
                "time": 2461194.5,
                "flux": 7100.0,
                "fluxerr": 350.0,
                "band": "lsstr",
                "zp": 31.4,
                "zpsys": "ab",
            },
        ],
    }
    data, candid = _normalize_ampel_report(report)
    _assert_standard_shape(data)
    assert data["objectId"] == "170463893335834628"
    # AMPEL bands "lssti"/"lsstr" -> passband letters (the save re-prefixes survey)
    assert [p["band"] for p in data["prv_candidates"]] == ["i", "r"]
    assert data["prv_candidates"][0]["psfFlux"] == 6053.6


def test_fink_survey_routing():
    assert _fink_survey(_MockBroker({"survey": "LSST"})) == "LSST"
    assert _fink_survey(_MockBroker({}), {"survey": "ztf"}) == "ZTF"
    assert FINKBROKER.implements()["query_alerts"] is True
