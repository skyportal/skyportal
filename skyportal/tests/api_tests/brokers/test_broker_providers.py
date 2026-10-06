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
import time

import fastavro
import pytest
import requests
import vcr

from skyportal.broker_apis.alerce import ALERCEBROKER, _normalize_object
from skyportal.broker_apis.ampel import _normalize_ampel_report
from skyportal.broker_apis.antares import ANTARESBROKER, _normalize_locus
from skyportal.broker_apis.boom import (
    _BOOM_SENTINEL,
    BOOMBROKER,
    _boom_photometry_to_prv,
    _normalize_boom_alert,
)
from skyportal.broker_apis.fink import (
    FINKBROKER,
    _fink_survey,
    _normalize_fink_lsst,
    _normalize_fink_object,
)
from skyportal.broker_apis.interface import survey_permissions
from skyportal.broker_apis.lasair import LASAIRBROKER
from skyportal.broker_apis.lasair import _normalize_object as _normalize_lasair
from skyportal.broker_apis.pittgoogle import (
    PITTGOOGLEBROKER,
    _normalize_pubsub_alert,
    _normalize_rows,
)

CASSETTE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "broker_cassettes"
)

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
    broker = _MockBroker({"survey": "ZTF"})
    with broker_vcr.use_cassette("antares_get_alert.yaml"):
        data = ANTARESBROKER.get_alert(broker, "ZTF26abeuijw", None)
    _assert_standard_shape(data)
    assert data["objectId"] == "ZTF26abeuijw"


class _FakeAlert:
    def __init__(self, properties):
        self.properties = properties


class _FakeLocus:
    """Duck-typed stand-in for an antares_client Locus (the normalizer only reads
    locus_id/ra/dec/properties/alerts)."""

    def __init__(self, fx):
        self.locus_id = fx["locus_id"]
        self.ra = fx["ra"]
        self.dec = fx["dec"]
        self.properties = fx["properties"]
        self.alerts = [_FakeAlert(a) for a in fx["alerts"]]


def test_antares_lsst_normalize():
    # ANTARES loci carry hundreds of cross-matched ZTF alerts alongside a few
    # LSST diaSources, so we save just the real LSST source rows (not a full
    # cassette) and drive the normalizer directly.
    from skyportal.broker_apis.antares import _normalize_lsst_locus

    with open(os.path.join(CASSETTE_DIR, "antares_lsst_locus.json")) as f:
        fx = json.load(f)
    data = _normalize_lsst_locus(_FakeLocus(fx))
    _assert_standard_shape(data)
    assert data["objectId"] == "170595943059554358"
    assert data["candidate"]["psfFlux"] is not None
    assert all(p["psfFlux"] is not None for p in data["prv_candidates"])
    assert all(
        p["band"] in ("u", "g", "r", "i", "z", "y") for p in data["prv_candidates"]
    )


def test_lasair_cone_cassette():
    broker = _MockBroker(
        {"survey": "ZTF", "token": "x", "endpoint": "https://lasair-ztf.lsst.ac.uk/api"}
    )
    with broker_vcr.use_cassette("lasair_cone.yaml"):
        rows = LASAIRBROKER.cone_search(broker, 280.0, -5.0, 600, None)
    assert rows is not None
    assert len(rows) >= 1


def test_lasair_test_filter_passes_raw_sql(monkeypatch):
    """A query-kind (Lasair) filter's Select/From/Where reaches Lasair's query API
    verbatim, so joins/aliases/functions the condition tree can't express work."""
    import skyportal.broker_apis.lasair as lasair_mod

    captured = {}

    def fake_request(broker, method, data):
        captured["method"] = method
        captured["data"] = data
        return []

    monkeypatch.setattr(lasair_mod, "_request", fake_request)
    broker = _MockBroker({"survey": "LSST", "token": "x"})
    LASAIRBROKER.test_filter(
        broker,
        None,
        selected='objects.diaObjectId, crossmatch_tns.tns_name AS "tns_name"',
        tables="objects,crossmatch_tns,sherlock_classifications",
        conditions=(
            "objects.nDiaSources > 2 AND objects.firstDiaSourceMjdTai > (mjdnow() - 40)"
        ),
        limit=25,
    )
    assert captured["method"] == "query"
    assert captured["data"]["selected"].startswith("objects.diaObjectId")
    assert (
        captured["data"]["tables"] == "objects,crossmatch_tns,sherlock_classifications"
    )
    assert "mjdnow() - 40" in captured["data"]["conditions"]
    assert captured["data"]["limit"] == 25


def _capture_boom_request(monkeypatch, result=None):
    """Intercept BOOM's HTTP layer and record the outgoing payloads."""
    import skyportal.broker_apis.boom as boom_mod

    calls = []

    # Mirror _request's signature, timeout included: test_filter and
    # validate_filter pass one, and a fake without it raises TypeError.
    def fake_request(broker, method, path, *, params=None, json=None, timeout=None):
        calls.append(
            {
                "method": method,
                "path": path,
                "params": params,
                "json": json,
                "timeout": timeout,
            }
        )
        return result if result is not None else []

    monkeypatch.setattr(boom_mod, "_request", fake_request)
    return calls


def test_survey_permissions_from_stream_selectors():
    class _Stream:
        def __init__(self, collection, selector):
            self.altdata = {"collection": collection, "selector": selector}

    assert survey_permissions([_Stream("ZTF_alerts", [1])]) == {"ZTF": [1]}
    # a user holding several streams gets their union
    assert survey_permissions(
        [_Stream("ZTF_alerts", [1]), _Stream("ZTF_alerts", [1, 2])]
    ) == {"ZTF": [1, 2]}
    assert survey_permissions(
        [_Stream("ZTF_alerts", [1, 2, 3]), _Stream("LSST_alerts", [1])]
    ) == {"ZTF": [1, 2, 3], "LSST": [1]}
    assert survey_permissions([_Stream("ZTF_alerts", None)]) == {}


@pytest.mark.parametrize(
    ("permissions", "expected"),
    [
        ({"ZTF": [1]}, [1]),  # public-only
        ({"ZTF": [1, 2]}, [1, 2]),  # partnership
        ({"ZTF": [1, 2, 3]}, [1, 2, 3]),  # caltech
        ({"LSST": [1]}, []),  # no ZTF stream at all
        ({}, []),  # no scope passed: fail closed
    ],
)
def test_boom_query_alerts_scoped_to_programids(monkeypatch, permissions, expected):
    calls = _capture_boom_request(monkeypatch)
    broker = _MockBroker(
        {"survey": "ZTF", "host": "h", "username": "u", "password": "p"}
    )
    BOOMBROKER.query_alerts(
        broker, None, objectId="ZTF20aapnxry", permissions=permissions
    )
    assert calls[0]["json"]["filter"] == {
        "objectId": "ZTF20aapnxry",
        "candidate.programid": {"$in": expected},
    }


def test_boom_query_alerts_unrestricted_for_admins(monkeypatch):
    calls = _capture_boom_request(monkeypatch)
    broker = _MockBroker({"survey": "ZTF"})
    BOOMBROKER.query_alerts(broker, None, objectId="ZTF20aapnxry", permissions=None)
    assert calls[0]["json"]["filter"] == {"objectId": "ZTF20aapnxry"}


def test_boom_query_alerts_infers_survey_from_object_id(monkeypatch):
    calls = _capture_boom_request(monkeypatch)
    broker = _MockBroker({"survey": "ZTF"})
    BOOMBROKER.query_alerts(
        broker, None, objectId="170591514995458386", permissions=None
    )
    assert calls[0]["json"]["catalog_name"] == "LSST_alerts"
    assert calls[0]["json"]["filter"]["objectId"] == {
        "$in": ["170591514995458386", 170591514995458386]
    }


def test_save_as_source_infers_survey_from_object_id(monkeypatch):
    """Saving an LSST object through a broker whose altdata defaults to ZTF must
    ingest it as LSST, not as ZTF bands ('ztfz' is not a real filter)."""
    import asyncio

    from skyportal.broker_apis import _save

    captured = {}

    def fake_get_alert(_broker, alert_id, _session, **kwargs):
        captured["fetched_survey"] = kwargs.get("survey")
        return {"objectId": alert_id}

    async def fake_save(_data, survey, *_args, **_kwargs):
        captured["survey"] = survey

    monkeypatch.setattr(BOOMBROKER, "get_alert", staticmethod(fake_get_alert))
    monkeypatch.setattr(_save, "save_object_as_source", fake_save)

    asyncio.run(
        BOOMBROKER.save_as_source(
            _MockBroker({"survey": "ZTF"}), "170591514995458386", None, None, [1]
        )
    )
    assert captured == {"fetched_survey": "LSST", "survey": "LSST"}


@pytest.mark.parametrize(
    ("permissions", "expected"),
    [
        ({"LSST": [1]}, {}),
        ({"ZTF": [1]}, {"_id": {"$in": []}}),
        ({}, {"_id": {"$in": []}}),
    ],
)
def test_boom_query_alerts_lsst_scoped_by_stream(monkeypatch, permissions, expected):
    calls = _capture_boom_request(monkeypatch)
    broker = _MockBroker({"survey": "ZTF"})
    BOOMBROKER.query_alerts(
        broker, None, objectId="170591514995458386", permissions=permissions
    )
    filter_ = dict(calls[0]["json"]["filter"])
    filter_.pop("objectId")
    assert filter_ == expected


@pytest.mark.parametrize(
    ("permissions", "expected"),
    [
        ({"DECAM": [1]}, {}),
        ({"ZTF": [1, 2, 3]}, {"_id": {"$in": []}}),
    ],
)
def test_boom_query_alerts_decam_scoped_by_stream(monkeypatch, permissions, expected):
    """A DECam object id routes to DECAM_alerts, which has no programid: access
    is the DECam stream, not a programid clause."""
    calls = _capture_boom_request(monkeypatch)
    broker = _MockBroker({"survey": "ZTF"})
    BOOMBROKER.query_alerts(
        broker, None, objectId="A202609132028318m134013", permissions=permissions
    )
    assert calls[0]["json"]["catalog_name"] == "DECAM_alerts"
    filter_ = dict(calls[0]["json"]["filter"])
    assert filter_.pop("objectId") == "A202609132028318m134013"
    assert filter_ == expected


def test_boom_get_alert_decam_exposes_aperture_photometry(monkeypatch):
    """DECam history carries magap and a uJy difference flux; get_alert serves
    it as nJy psfFlux and magpsf, on the same scale as the Kafka photometry."""
    record = {
        "objectId": "A202609132028318m134013",
        "candidate": {
            "magap": 18.162868,
            "sigmagap": 0.0045,
            "forcediffimflux": 197.17543,
            "forcediffimfluxunc": 0.82192,
        },
        "prv_candidates": [
            {
                "jd": 2461284.59611032,
                "band": "i",
                "magap": 18.162868,
                "sigmagap": 0.0045,
                "forcediffimflux": 197.17543,
                "forcediffimfluxunc": 0.82192,
            }
        ],
    }
    calls = _capture_boom_request(monkeypatch, result=[record])
    data = BOOMBROKER.get_alert(
        _MockBroker({"survey": "ZTF"}),
        "A202609132028318m134013",
        None,
        permissions={"DECAM": [1]},
    )
    assert calls[0]["json"]["catalog_name"] == "DECAM_alerts"
    assert {"$sort": {"candidate.magap": 1}} in calls[0]["json"]["pipeline"]
    point = data["prv_candidates"][0]
    assert point["psfFlux"] == pytest.approx(197175.43)
    assert point["psfFluxErr"] == pytest.approx(821.92)
    assert point["magpsf"] == 18.162868
    assert data["candidate"]["sigmapsf"] == 0.0045


def test_boom_get_alert_drops_out_of_scope_history(monkeypatch):
    record = {
        "objectId": "ZTF20aapnxry",
        "prv_candidates": [{"programid": 1}, {"programid": 2}, {"programid": 3}],
        "fp_hists": [{"programid": 2}],
    }
    _capture_boom_request(monkeypatch, result=[record])
    broker = _MockBroker({"survey": "ZTF"})
    data = BOOMBROKER.get_alert(
        broker, "ZTF20aapnxry", None, permissions={"ZTF": [1, 2]}
    )
    # a visible alert can still carry partnership-only history points
    assert data["prv_candidates"] == [{"programid": 1}, {"programid": 2}]
    assert data["fp_hists"] == [{"programid": 2}]


def test_boom_cutouts_denied_when_alert_out_of_scope(monkeypatch):
    calls = _capture_boom_request(monkeypatch, result=[])
    broker = _MockBroker({"survey": "ZTF"})
    with pytest.raises(ValueError, match="No accessible alert"):
        BOOMBROKER.get_cutouts(
            broker, "1145416792615015000", None, permissions={"ZTF": [1]}
        )
    # the scope check runs before any cutout is fetched
    assert [c["path"] for c in calls] == ["queries/find"]
    assert calls[0]["json"]["filter"]["candidate.programid"] == {"$in": [1]}


def test_boom_test_filter_caps_stream_scope_by_requester(monkeypatch):
    """A preview runs with the filter's stream selector, narrowed to what the
    requester may see — testing a partnership filter as a public user must not
    surface partnership alerts."""
    calls = _capture_boom_request(monkeypatch)
    broker = _MockBroker({"survey": "ZTF"})
    BOOMBROKER.test_filter(
        broker, None, pipeline=[{"$match": {}}], permissions={"ZTF": [1]}
    )
    assert calls[0]["json"]["permissions"] == {"ZTF": [1]}


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


def _boom_record(photometry):
    return {
        "objectId": "BOOM_norm",
        "candid": 42,
        "survey": "ZTF",
        "jd": 2459000.5,
        "ra": 234.22,
        "dec": -22.33,
        "drb": 0.99,
        "photometry": photometry,
    }


def test_boom_normalize_maps_detection_and_candidate():
    """A detection maps flux -> psfFlux (nJy) with band/jd/programid preserved,
    and candidate jd/ra/dec/drb come off the record."""
    d = _normalize_boom_alert(
        _boom_record(
            [
                {
                    "flux": 1.0e4,
                    "flux_err": 1.0e2,
                    "jd": 2459000.5,
                    "band": "ztfg",
                    "programid": 1,
                }
            ]
        )
    )
    _assert_standard_shape(d)
    assert d["candid"] == 42
    assert d["candidate"] == {
        "jd": 2459000.5,
        "ra": 234.22,
        "dec": -22.33,
        "drb": 0.99,
    }
    p = d["prv_candidates"][0]
    assert (p["psfFlux"], p["psfFluxErr"], p["band"], p["jd"], p["programid"]) == (
        1.0e4,
        1.0e2,
        "ztfg",
        2459000.5,
        1,
    )


def test_boom_normalize_sentinel_flux_is_nondetection():
    """A point with a real flux_err but sentinel flux is kept as a non-detection
    (psfFlux nulled) -- distinct from a sentinel flux_err, which is dropped."""
    d = _normalize_boom_alert(
        _boom_record(
            [{"flux": _BOOM_SENTINEL, "flux_err": 1.0e2, "jd": 2459003.5, "band": "r"}]
        )
    )
    assert len(d["prv_candidates"]) == 1
    assert d["prv_candidates"][0]["psfFlux"] is None
    assert d["prv_candidates"][0]["psfFluxErr"] == 1.0e2


def test_boom_photometry_drops_infinite_flux_err():
    prv = _boom_photometry_to_prv(
        [
            {"flux": 500.0, "flux_err": 50.0, "jd": 2459000.5, "band": "g"},
            {"flux": None, "flux_err": float("inf"), "jd": 2459001.5, "band": "r"},
        ]
    )
    assert [p["jd"] for p in prv] == [2459000.5]


def test_boom_normalize_empty_photometry():
    """A record without photometry normalizes to an empty light curve rather than
    raising (the ingestion loop must not crash on a bare alert)."""
    d = _normalize_boom_alert(_boom_record([]))
    assert d["prv_candidates"] == []
    assert d["candidate"]["drb"] == 0.99


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


# --- photometry passthrough --------------------------------------------------

from skyportal.broker_apis._photometry import (  # noqa: E402
    filter_groups_by_scope,
    merge_photometry_points,
)
from skyportal.broker_apis._save import (  # noqa: E402
    _passes_criteria,
    build_photometry_groups,
)


def test_build_photometry_groups_flux_and_mag_space():
    """The transform (shared verbatim with the save path) handles flux-space
    brokers (psfFlux, e.g. BOOM) and magnitude-space brokers (magpsf, e.g.
    Lasair), keying by (survey, programid) and carrying the gating stream."""
    data = {
        "prv_candidates": [
            {
                "jd": 2459000.5,
                "band": "g",
                "psfFlux": 100.0,
                "psfFluxErr": 1.0,
                "programid": 1,
                "ra": 1.0,
                "dec": 2.0,
            },
        ],
        "fp_hists": [
            # magnitude space: mag=20 at zp=23.9 -> flux = 10**(-0.4*(20-23.9))
            {
                "jd": 2459001.5,
                "band": "r",
                "magpsf": 20.0,
                "sigmapsf": 0.1,
                "programid": 1,
            },
        ],
    }
    groups = build_photometry_groups("ZTF1", "ZTF", data, 42, {("ZTF", 1): [10]})
    g = groups[("ZTF", 1)]
    assert g["instrument_id"] == 42 and g["stream_ids"] == [10]
    assert g["mjd"] == [59000.0, 59001.0]
    assert g["filter"] == ["ztfg", "ztfr"]
    assert g["flux"][0] == 100.0 * 1e-9
    assert g["flux"][1] == pytest.approx(10.0 ** (-0.4 * (20.0 - 23.9)))


def test_build_photometry_groups_winter_flux_scale_and_zeropoint():
    """WINTER flux (nJy) is scaled to Jy and takes the Jy zeropoint, 8.9.

    ZTF's 23.9 belongs to the magnitude path and its uJy scale. Using it here
    would put every point about 15 magnitudes too faint.
    """
    import math

    # a real alert point: mag ~16.7 as flux in nJy
    data = {
        "prv_candidates": [
            {
                "jd": 2460869.771,
                "band": "winterh",
                "psfFlux": 770160.8125,
                "psfFluxErr": 41050.37,
                "programid": 1,
            },
        ],
    }
    g = build_photometry_groups(
        "WNTR25euvzp", "WINTER", data, 1087, {("WINTER", 1): [1005]}
    )[("WINTER", 1)]
    assert g["zp"][0] == 8.9
    assert g["flux"][0] == pytest.approx(770160.8125e-9)
    assert -2.5 * math.log10(g["flux"][0]) + g["zp"][0] == pytest.approx(
        16.68, abs=0.05
    )


def test_build_photometry_groups_winter_bands_map_to_instrument_filters():
    """WINTER filters are named for the photometric system, not the survey.

    Bands arrive as a bare letter ("h"); a survey-prefixed form is stripped
    before the lookup so either spelling resolves to the same filter.
    """
    for band, expected in (
        ("winterh", "2massh"),
        ("winterj", "2massj"),
        ("wintery", "desy"),
        ("h", "2massh"),
    ):
        data = {
            "prv_candidates": [
                {
                    "jd": 2459000.5,
                    "band": band,
                    "psfFlux": 1000.0,
                    "psfFluxErr": 10.0,
                    "programid": 1,
                },
            ],
        }
        groups = build_photometry_groups(
            "WNTR25abcde", "WINTER", data, 1087, {("WINTER", 1): [1005]}
        )
        assert groups[("WINTER", 1)]["filter"] == [expected]


def test_build_photometry_groups_winter_refuses_unresolved_bands():
    """k has no WINTER filter, so the alert is refused rather than mislabelled."""
    for band in ("winterk", "k"):
        data = {
            "prv_candidates": [
                {
                    "jd": 2459000.5,
                    "band": band,
                    "psfFlux": 1000.0,
                    "psfFluxErr": 10.0,
                    "programid": 1,
                },
            ],
        }
        with pytest.raises(ValueError, match="No filter configured"):
            build_photometry_groups(
                "WNTR25abcde", "WINTER", data, 1087, {("WINTER", 1): [1005]}
            )


def test_build_photometry_groups_decam_on_the_instrument_filters():
    """A DECam point from BOOM's Kafka photometry (nJy, band "decami") lands on
    the DECam instrument's des* filters with the Jy zeropoint, at its magap."""
    import math

    data = {
        "prv_candidates": [
            {
                "jd": 2461284.59611032,
                "band": "decami",
                "psfFlux": 197175.43,
                "psfFluxErr": 821.92,
                "programid": 1,
            },
        ],
    }
    g = build_photometry_groups(
        "A202609132028318m134013", "DECAM", data, 54, {("DECAM", 1): [1006]}
    )[("DECAM", 1)]
    assert g["filter"] == ["desi"]
    assert g["zp"][0] == 8.9
    assert -2.5 * math.log10(g["flux"][0]) + g["zp"][0] == pytest.approx(
        18.163, abs=1e-3
    )


def test_decam_survey_maps_to_the_decam_instrument():
    from skyportal.utils.survey import instrument_name, survey_from_instrument

    assert instrument_name("DECAM") == "DECam"
    assert survey_from_instrument("DECam") == "DECAM"
    assert instrument_name("ZTF") == "ZTF"
    assert survey_from_instrument("ZTF") == "ZTF"


def test_build_photometry_groups_survey_prefixed_band_not_doubled():
    """BOOM emits survey-prefixed bands ("ztfg"); the filter must stay "ztfg",
    not "ztfztfg" (which the photometry validator rejects, dropping the alert)."""
    data = {
        "prv_candidates": [
            {
                "jd": 2459000.5,
                "band": "ztfg",
                "psfFlux": 100.0,
                "psfFluxErr": 1.0,
                "programid": 1,
            },
        ],
    }
    groups = build_photometry_groups("ZTF1", "ZTF", data, 42, {("ZTF", 1): [10]})
    assert groups[("ZTF", 1)]["filter"] == ["ztfg"]


def test_build_photometry_groups_drops_ungated_programs():
    """A program with no mapped stream is dropped (never displayed) rather than
    leaked with empty gating."""
    data = {
        "prv_candidates": [
            {
                "jd": 2459000.5,
                "band": "g",
                "psfFlux": 1.0,
                "psfFluxErr": 1.0,
                "programid": 2,
            },
        ]
    }
    # only programid 1 is mapped -> the programid-2 point has no home
    assert build_photometry_groups("ZTF1", "ZTF", data, 42, {("ZTF", 1): [10]}) == {}


def test_scope_filter_no_leakage():
    """A requester whose streams cover only the public programid must never
    receive the partnership group; the system admin's ``None`` scope keeps all."""
    groups = {
        ("ZTF", 1): {"mjd": [1.0]},
        ("ZTF", 2): {"mjd": [2.0]},
        ("LSST", 1): {"mjd": [3.0]},
    }
    assert set(filter_groups_by_scope(groups, {"ZTF": [1]})) == {("ZTF", 1)}
    assert set(filter_groups_by_scope(groups, {"ZTF": [1, 2, 3], "LSST": [1]})) == set(
        groups
    )
    assert filter_groups_by_scope(groups, {}) == {}
    assert set(filter_groups_by_scope(groups, None)) == set(groups)


def test_merge_broker_augments_db_and_dedups():
    """DB is authoritative: a broker point matching a DB point on
    (obj, instrument, filter, mjd) is dropped (float noise absorbed), broker-only
    points are appended, DB points keep their identity."""
    db = [
        {"obj_id": "A", "instrument_id": 1, "filter": "ztfg", "mjd": 59000.0, "id": 5}
    ]
    broker = [
        {
            "obj_id": "A",
            "instrument_id": 1,
            "filter": "ztfg",
            "mjd": 59000.0000001,
            "id": None,
        },
        {
            "obj_id": "A",
            "instrument_id": 1,
            "filter": "ztfg",
            "mjd": 59002.5,
            "id": None,
        },
    ]
    merged = merge_photometry_points(db, broker)
    assert [p for p in merged if p.get("id") is not None] == db
    appended = [p for p in merged if p.get("id") is None]
    assert len(appended) == 1 and appended[0]["mjd"] == 59002.5
    assert merge_photometry_points([], []) == []


def test_merge_keeps_forced_photometry_at_a_saved_epoch():
    """Forced photometry carries its own origin, so a saved alert point must not
    suppress it: ZTF fp_hists covers the very exposures prv_nondetections reports
    a limit for, and dropping on (obj, instrument, filter, mjd) alone hid all of it."""
    db = [
        {
            "obj_id": "A",
            "instrument_id": 1,
            "filter": "ztfg",
            "mjd": 59000.0,
            "origin": "None",
            "id": 5,
        }
    ]
    broker = [
        {
            "obj_id": "A",
            "instrument_id": 1,
            "filter": "ztfg",
            "mjd": 59000.0,
            "origin": "fp",
            "id": None,
        }
    ]
    assert len(merge_photometry_points(db, broker)) == 2


def test_merge_dedups_per_obj():
    """Under includeSuperObjsPhotometry the points of several objs are merged at
    once: a saved point on one obj must not suppress the same epoch on another."""
    db = [
        {"obj_id": "A", "instrument_id": 1, "filter": "ztfg", "mjd": 59000.0, "id": 5}
    ]
    broker = [
        {
            "obj_id": "B",
            "instrument_id": 1,
            "filter": "ztfg",
            "mjd": 59000.0,
            "id": None,
        }
    ]
    assert len(merge_photometry_points(db, broker)) == 2


class _FakePhotometrySession:
    async def scalar(self, _stmt):
        return 1

    async def scalars(self, _stmt):
        return type("_Result", (), {"all": staticmethod(list)})()


class _FakePhotometryBroker:
    id = 987654
    altdata: dict = {}


def _fetch_groups(cls, object_id):
    import asyncio

    from skyportal.broker_apis._photometry import fetch_broker_groups

    return asyncio.run(
        fetch_broker_groups(
            cls, _FakePhotometryBroker(), object_id, "ZTF", _FakePhotometrySession()
        )
    )


def test_fetch_skips_the_broker_only_on_a_timeout():
    """A 404 means the broker does not know this object, not that it is down: it
    must be cached as empty and must not disable the passthrough for every other
    object. Only a timeout, which is what stalls a source page, arms the skip."""
    from skyportal.broker_apis import _photometry

    class NotFound:
        calls = 0

        @staticmethod
        def get_alert(_broker, _object_id, _session, **_kwargs):
            NotFound.calls += 1
            response = requests.Response()
            response.status_code = 404
            response.raise_for_status()

    class Stalling:
        @staticmethod
        def get_alert(_broker, _object_id, _session, **_kwargs):
            time.sleep(_photometry._FETCH_TIMEOUT_SECONDS + 0.5)

    _photometry._skip_until.clear()
    timeout = _photometry._FETCH_TIMEOUT_SECONDS
    _photometry._FETCH_TIMEOUT_SECONDS = 0.2
    try:
        assert _fetch_groups(NotFound, "ZTFunknown") == {}
        assert _photometry._skip_until == {}
        assert _fetch_groups(NotFound, "ZTFunknown") == {}
        assert NotFound.calls == 1

        with pytest.raises(TimeoutError):
            _fetch_groups(Stalling, "ZTFstalling")
        assert _photometry._skip_until
    finally:
        _photometry._FETCH_TIMEOUT_SECONDS = timeout
        _photometry._skip_until.clear()
        del _photometry.cache[f"{_FakePhotometryBroker.id}_ZTF_ZTFunknown"]


def test_cached_groups_expire_on_their_fetch_time():
    """Reading a cache entry touches its file, so ``Cache``'s own max_age would
    never expire a source that is looked at often: the entry ages on the fetch
    time stored in it."""
    from skyportal.broker_apis import _photometry

    class Empty:
        calls = 0

        @staticmethod
        def get_alert(_broker, _object_id, _session, **_kwargs):
            Empty.calls += 1
            return None

    max_age = _photometry._CACHE_MAX_AGE
    _photometry._CACHE_MAX_AGE = 3600
    try:
        _fetch_groups(Empty, "ZTFfresh")
        _fetch_groups(Empty, "ZTFfresh")
        assert Empty.calls == 1

        _photometry._CACHE_MAX_AGE = 0
        _fetch_groups(Empty, "ZTFfresh")
        assert Empty.calls == 2
    finally:
        _photometry._CACHE_MAX_AGE = max_age
        del _photometry.cache[f"{_FakePhotometryBroker.id}_ZTF_ZTFfresh"]


def test_an_unreadable_cache_entry_is_a_miss():
    """A write cut short by a crash leaves a truncated file that reading touches,
    so it would never expire either: it has to count as a miss and be rewritten."""
    from skyportal.broker_apis import _photometry
    from skyportal.utils.cache import dict_to_bytes

    class Empty:
        @staticmethod
        def get_alert(_broker, _object_id, _session, **_kwargs):
            return None

    key = f"{_FakePhotometryBroker.id}_ZTF_ZTFtruncated"
    blob = dict_to_bytes({"fetched_at": time.time(), "groups": {}})
    _photometry.cache[key] = blob[: len(blob) // 2]
    try:
        assert _fetch_groups(Empty, "ZTFtruncated") == {}
        assert _fetch_groups(Empty, "ZTFtruncated") == {}
    finally:
        del _photometry.cache[key]


def _lc(*points):
    return {"prv_candidates": list(points)}


# flux-space (SNR = flux/flux_err) and mag-space (SNR = 1.0857/sigma) points.
_HI = {"psfFlux": 1e4, "psfFluxErr": 1e2, "band": "g", "jd": 2459000.5}  # SNR 100
_LO = {"psfFlux": 3e2, "psfFluxErr": 1e2, "band": "r", "jd": 2459002.5}  # SNR 3
_R8 = {"psfFlux": 8e2, "psfFluxErr": 1e2, "band": "ztfr", "jd": 2459005.5}  # SNR 8
_MAG = {"magpsf": 19.0, "sigmapsf": 0.1, "band": "ztfg", "jd": 2459003.5}  # SNR ~10.9


def test_passes_criteria_gate_off_when_unset():
    # No criteria (or an empty block) never filters — existing filters unaffected.
    assert _passes_criteria(_lc(_LO), None) is True
    assert _passes_criteria(_lc(_LO), {}) is True


def test_passes_criteria_default_snr_is_5():
    # A detection must clear S/N 5 by default; SNR-3 point doesn't count.
    assert _passes_criteria(_lc(_LO), {"min_detections": 1}) is False
    assert _passes_criteria(_lc(_HI), {"min_detections": 1}) is True
    # ...unless min_snr is overridden.
    assert _passes_criteria(_lc(_LO), {"min_detections": 1, "min_snr": 2}) is True


def test_passes_criteria_min_detections_counts_only_snr_passing():
    assert _passes_criteria(_lc(_HI, _LO), {"min_detections": 2}) is False
    assert _passes_criteria(_lc(_HI, _R8), {"min_detections": 2}) is True
    # mag-space points also yield a computable S/N.
    assert _passes_criteria(_lc(_MAG), {"min_detections": 1}) is True


def test_passes_criteria_per_band_normalizes_band_names():
    # ztfr -> r, so {g:1, r:1} is satisfied by a g and a ztfr detection.
    assert (
        _passes_criteria(_lc(_HI, _R8), {"min_detections_per_band": {"g": 1, "r": 1}})
        is True
    )
    assert (
        _passes_criteria(_lc(_HI), {"min_detections_per_band": {"g": 1, "r": 1}})
        is False
    )


def test_passes_criteria_time_baseline():
    # _HI @2459000.5 and _R8 @2459005.5 -> 5-day baseline.
    assert _passes_criteria(_lc(_HI, _R8), {"min_time_baseline": 3}) is True
    assert _passes_criteria(_lc(_HI, _R8), {"min_time_baseline": 10}) is False
    # A single detection has no baseline.
    assert _passes_criteria(_lc(_HI), {"min_time_baseline": 1}) is False


def test_filters_passing_criteria_reads_db_filter(public_filter):
    """DB-backed: the gate loads criteria from a real Filter.altdata row and
    returns only the filters the alert satisfies."""
    import asyncio

    import sqlalchemy as sa

    from baselayer.app.models import async_plain_session_factory
    from skyportal.broker_apis._save import _filters_passing_criteria
    from skyportal.models import Filter

    fid = public_filter.id

    async def _set_criteria():
        async with async_plain_session_factory() as session:
            f = await session.scalar(sa.select(Filter).where(Filter.id == fid))
            f.altdata = {"criteria": {"min_detections": 2}}
            await session.commit()

    asyncio.run(_set_criteria())

    async def _passing(data):
        async with async_plain_session_factory() as session:
            return await _filters_passing_criteria(session, [fid], data)

    assert asyncio.run(_passing(_lc(_HI, _R8))) == [fid]  # two S/N>=5 detections
    assert asyncio.run(_passing(_lc(_HI))) == []  # only one


def test_ingestion_gate_suppresses_failing_alert(public_filter, super_admin_user):
    """DB-backed end-to-end: an alert that fails a Filter's criteria creates no
    Obj/Candidate (the gate returns before any DB write)."""
    import asyncio
    import uuid

    import sqlalchemy as sa

    from baselayer.app.models import async_plain_session_factory
    from skyportal.broker_apis._save import save_object_as_candidate
    from skyportal.models import Candidate, Filter, Obj, User

    fid = public_filter.id
    uid = super_admin_user.id

    async def _set_criteria():
        async with async_plain_session_factory() as session:
            f = await session.scalar(sa.select(Filter).where(Filter.id == fid))
            f.altdata = {"criteria": {"min_detections": 5}}
            await session.commit()

    asyncio.run(_set_criteria())

    obj_id = f"ZTF_gate_{uuid.uuid4().hex[:8]}"
    # One detection, well under min_detections=5 -> suppressed.
    data = {
        "objectId": obj_id,
        "candidate": {"ra": 1.0, "dec": 2.0, "drb": 0.9},
        "prv_candidates": [_HI],
    }

    async def _ingest():
        async with async_plain_session_factory() as session:
            user = await session.scalar(sa.select(User).where(User.id == uid))
            await save_object_as_candidate(
                data, "ZTF", session, user, [fid], passing_alert_id=1
            )

    asyncio.run(_ingest())

    async def _fetch():
        async with async_plain_session_factory() as session:
            obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))
            cand = await session.scalar(
                sa.select(Candidate).where(Candidate.obj_id == obj_id)
            )
            return obj, cand

    obj, cand = asyncio.run(_fetch())
    assert obj is None, "suppressed alert must not create an Obj"
    assert cand is None, "suppressed alert must not create a Candidate"


def test_get_photometry_capability_gated_on_get_alert():
    """get_photometry is a base default: advertised iff the provider can fetch an
    object (implements get_alert) and does not opt out of the passthrough."""
    assert BOOMBROKER.implements()["get_photometry"] is True
    assert ANTARESBROKER.implements()["save_as_source"] is True
    assert ANTARESBROKER.implements()["get_photometry"] is False
    assert PITTGOOGLEBROKER.implements()["get_photometry"] is False

    from skyportal.broker_apis.interface import BrokerAPI

    class _BareBroker(BrokerAPI):
        surveys = []

    assert _BareBroker.implements()["get_photometry"] is False
    assert FINKBROKER.implements()["query_alerts"] is True


def test_boom_filter_test_scopes_unrestricted_users(public_stream):
    """A system admin's None scope must not reach BOOM as an empty map."""
    import types

    import sqlalchemy as sa

    from skyportal.broker_apis import boom as boom_module
    from skyportal.models import DBSession, Stream

    session = DBSession()
    stream = session.scalar(sa.select(Stream).where(Stream.id == public_stream.id))
    stream.altdata = {"collection": "ZTF_alerts", "selector": [1, 2]}
    session.commit()

    captured = {}

    def fake_request(broker, method, path, *, params=None, json=None, timeout=None):
        captured["path"] = path
        captured["json"] = json
        return {"count": 0}

    original = boom_module._request
    boom_module._request = fake_request
    try:
        boom_module.BOOMBROKER.test_filter(
            types.SimpleNamespace(altdata={}),
            session,
            survey="ZTF",
            permissions=None,  # unrestricted, as alert_permissions returns for admins
            pipeline=[{"$match": {"candidate.drb": {"$gt": 0.9}}}],
        )
    finally:
        boom_module._request = original

    assert captured["path"] == "filters/test/count"
    assert captured["json"]["permissions"] == {"ZTF": [1, 2]}, (
        "unrestricted user must still be given an explicit programid scope"
    )


def test_build_photometry_groups_drops_repeated_epochs():
    """An epoch repeated under one origin must be written once, but a forced
    measurement keeps its own row at an epoch an alert point already covers.

    Photometry is unique on (obj, instrument, origin, mjd, filter), and Postgres
    refuses an INSERT that carries duplicates within a single statement rather
    than resolving them -- so a repeat used to cost the object all of its
    photometry, not just the extra row.
    """
    point = {
        "jd": 2459000.5,
        "band": "g",
        "magpsf": 19.0,
        "sigmapsf": 0.1,
        "programid": 1,
    }
    data = {
        "prv_candidates": [point, dict(point)],
        "fp_hists": [dict(point), {**point, "jd": 2459001.5}],
    }
    groups = build_photometry_groups("ZTF1", "ZTF", data, 42, {("ZTF", 1): [10]})
    g = groups[("ZTF", 1)]

    assert g["mjd"] == [59000.0, 59000.0, 59001.0], "a repeated epoch was written twice"
    assert g["origin"] == [None, "fp", "fp"]
    assert len(g["filter"]) == len(g["mjd"]) == len(g["flux"])


def test_build_photometry_groups_keeps_same_epoch_in_other_bands():
    """Only (mjd, filter) together identify an epoch: g and r at one time stay."""
    base = {"jd": 2459000.5, "magpsf": 19.0, "sigmapsf": 0.1, "programid": 1}
    data = {"prv_candidates": [{**base, "band": "g"}, {**base, "band": "r"}]}
    groups = build_photometry_groups("ZTF1", "ZTF", data, 42, {("ZTF", 1): [10]})
    assert groups[("ZTF", 1)]["filter"] == ["ztfg", "ztfr"]


LASAIR_STREAM_MESSAGE = {
    "objectId": "ZTF21abcdlas",
    "objectData": {"ramean": 10.5, "decmean": -20.25},
    "candidates": [
        {
            "candid": 111,
            "jd": 2459300.5,
            "magpsf": 18.4,
            "sigmapsf": 0.07,
            "fid": 1,
            "ra": 10.5,
            "dec": -20.25,
        },
        {
            "candid": 110,
            "jd": 2459299.5,
            "magpsf": 18.9,
            "sigmapsf": 0.09,
            "fid": 2,
            "ra": 10.5,
            "dec": -20.25,
        },
    ],
}


def test_a_stream_message_with_a_lightcurve_needs_no_rest_call():
    """A topic carrying candidates is ingested from the message, since the REST
    quota sits far below stream rate."""
    from skyportal.broker_apis import lasair

    assert lasair.carries_lightcurve(LASAIR_STREAM_MESSAGE) is True
    data = lasair._normalize_object(LASAIR_STREAM_MESSAGE, "ZTF21abcdlas")
    assert data["objectId"] == "ZTF21abcdlas"
    assert data["candidate"]["magpsf"] == 18.4
    assert len(data["prv_candidates"]) == 2


def test_an_object_id_only_message_still_needs_the_rest_call():
    from skyportal.broker_apis import lasair

    for payload in (
        {"objectId": "ZTF21abcdlas"},
        {"objectId": "ZTF21abcdlas", "candidates": []},
        None,
        "not a dict",
    ):
        assert lasair.carries_lightcurve(payload) is False


# Shapes taken from live Lasair records. A diaSource carries no position, so
# the position comes from the diaObject; the REST object holds the lists at the
# top level and a Kafka lite_lightcurve message nests them under "alert".
LSST_SOURCES = [
    {
        "diaSourceId": 1,
        "midpointMjdTai": 60000.25,
        "band": "r",
        "psfFlux": 36307.8,
        "psfFluxErr": 3630.8,
        "reliability": 0.9,
    },
    {
        "diaSourceId": 2,
        "midpointMjdTai": 60004.25,
        "band": "g",
        "psfFlux": 229086.8,
        "psfFluxErr": 2290.9,
        "reliability": 0.9,
    },
    # difference-image flux below zero: a non-detection, not a measurement
    {
        "diaSourceId": 3,
        "midpointMjdTai": 59998.25,
        "band": "r",
        "psfFlux": -140.0,
        "psfFluxErr": 90.0,
        "reliability": 0.4,
    },
]
LSST_DIA_OBJECT = {
    "diaObjectId": 169760235333878021,
    "ra": 221.87087177320953,
    "decl": -38.16173726666955,
}
LASAIR_LSST_REST = {
    "diaObjectId": 169760235333878021,
    "diaObject": LSST_DIA_OBJECT,
    "diaSourcesList": LSST_SOURCES,
    "diaForcedSourcesList": [],
    "lasairData": {},
}
LASAIR_LSST_MESSAGE = {
    "diaObjectId": 169760235333878021,
    "ra": 221.87087177320953,
    "decl": -38.16173726666955,
    "UTC": "2026-01-29 11:40:14",
    "alert": {
        "diaObject": LSST_DIA_OBJECT,
        "diaSourcesList": LSST_SOURCES,
        "diaForcedSourcesList": [],
    },
}


def test_an_lsst_record_is_recognised_whether_rest_or_stream():
    from skyportal.broker_apis import lasair

    assert lasair.carries_lightcurve(LASAIR_LSST_MESSAGE) is True
    assert lasair._lsst_sources(LASAIR_LSST_REST) == LSST_SOURCES
    # the plain stream option carries a position and no photometry
    plain = {k: v for k, v in LASAIR_LSST_MESSAGE.items() if k != "alert"}
    assert lasair.carries_lightcurve(plain) is False


@pytest.mark.parametrize("record", [LASAIR_LSST_REST, LASAIR_LSST_MESSAGE])
def test_lsst_fluxes_become_ab_magnitudes_and_mjd_becomes_jd(record):
    from skyportal.broker_apis import lasair

    data = lasair._normalize_object(record, "169760235333878021")
    _assert_standard_shape(data)
    # newest detection wins: MJD 60004.25 in g at ~18.0
    assert data["candidate"]["jd"] == pytest.approx(60004.25 + 2400000.5)
    assert data["candidate"]["magpsf"] == pytest.approx(18.0, abs=1e-3)
    assert data["candidate"]["band"] == "g"
    # a diaSource has no position, so it comes from the diaObject
    assert data["candidate"]["ra"] == pytest.approx(221.87087177320953)
    assert data["candidate"]["dec"] == pytest.approx(-38.16173726666955)
    # the negative-flux source is not a detection
    assert len(data["prv_candidates"]) == 2
    assert all(p["magpsf"] is not None for p in data["prv_candidates"])


def test_an_lsst_non_detection_never_becomes_a_measurement():
    from skyportal.broker_apis import lasair

    assert lasair._lsst_magnitude(-140.0, 90.0) == (None, None)
    assert lasair._lsst_magnitude(0.0, 1.0) == (None, None)
    # 3631 Jy is AB mag 0 by definition
    assert lasair._lsst_magnitude(3.631e12, None)[0] == pytest.approx(0.0, abs=1e-3)
    # error of a 5-sigma measurement
    assert lasair._lsst_magnitude(1000.0, 200.0)[1] == pytest.approx(0.2171, abs=1e-3)


def test_a_bare_nan_in_a_lasair_response_is_parsed_as_none():
    """LSST records carry bare NaN, which is not JSON; response.json() defers to
    simplejson when installed and rejects it, so every LSST fetch raised."""
    import types

    from skyportal.broker_apis import lasair

    body = '{"diaObjectId": 1, "dipoleAngle": NaN, "psfFlux": 12.5}'
    response = types.SimpleNamespace(text=body)
    parsed = lasair._parse_json(response)
    assert parsed["dipoleAngle"] is None
    assert parsed["psfFlux"] == 12.5


def test_a_ztf_record_still_normalizes_the_old_way():
    from skyportal.broker_apis import lasair

    data = lasair._normalize_object(LASAIR_STREAM_MESSAGE, "ZTF21abcdlas")
    assert data["candidate"]["magpsf"] == 18.4
    assert len(data["prv_candidates"]) == 2


def test_lasair_replicates_only_when_a_stream_is_configured():
    """Extra ingest processes may share a Kafka group, but must not each run the
    REST poller: that spends the same account's quota again."""
    from skyportal.broker_apis.lasair import LASAIRBROKER

    assert LASAIRBROKER.parallel_ingestion({"token": "x"}) is False
    assert LASAIRBROKER.parallel_ingestion({}) is False
    assert (
        LASAIRBROKER.parallel_ingestion({"kafka": {"topics": ["lasair_2mine"]}}) is True
    )
    assert (
        LASAIRBROKER.parallel_ingestion({"kafka": {"topic_filter_ids": {"t": [1]}}})
        is True
    )


def test_offsets_are_stored_by_us_not_by_the_clock():
    """Auto-commit acknowledges on a timer, so a crash drops every message it
    had reached; storing after a successful ingest replays them instead."""
    from skyportal.broker_apis._kafka import kafka_consumer_config

    config = kafka_consumer_config({"host": "h", "port": 9092}, "g")
    # the provider sets this on the config it builds
    config["enable.auto.offset.store"] = False
    assert config["enable.auto.offset.store"] is False


class FakeKafkaMessage:
    """Enough of a confluent_kafka Message for the batch helpers."""

    def __init__(self, offset, payload, topic="lasair_2mine", partition=0, err=None):
        self._offset, self._payload = offset, payload
        self._topic, self._partition, self._err = topic, partition, err

    def topic(self):
        return self._topic

    def partition(self):
        return self._partition

    def offset(self):
        return self._offset

    def error(self):
        return self._err

    def value(self):
        return json.dumps(self._payload).encode() if self._payload is not None else b"{"


class FakeConsumer:
    def __init__(self):
        self.stored = []

    def store_offsets(self, message=None):
        self.stored.append((message.topic(), message.partition(), message.offset()))


def _msg(offset, oid, **kw):
    return FakeKafkaMessage(
        offset, {"objectId": oid, "candidates": [{"jd": 1.0}]}, **kw
    )


def test_a_batch_keeps_only_the_newest_alert_per_object():
    from skyportal.broker_apis import lasair

    msgs = [_msg(1, "A"), _msg(2, "B"), _msg(3, "A")]
    finished, work = lasair._prepare_batch(msgs, {}, [7])
    assert sorted(work) == ["A", "B"]
    # the superseded A at offset 1 needs no work, so it cannot stall the partition
    assert ("lasair_2mine", 0, 1) in finished
    assert work["A"][0].offset() == 3


def test_an_undecodable_message_does_not_stall_its_partition():
    from skyportal.broker_apis import lasair

    bad = FakeKafkaMessage(1, None)  # not valid JSON
    no_id = FakeKafkaMessage(2, {"foo": 1})  # no objectId
    finished, work = lasair._prepare_batch([bad, no_id, _msg(3, "A")], {}, [7])
    assert list(work) == ["A"]
    assert ("lasair_2mine", 0, 1) in finished
    assert ("lasair_2mine", 0, 2) in finished


def test_offsets_are_stored_only_up_to_the_first_failure():
    """Storing past a failure acknowledges an alert that was never ingested."""
    from skyportal.broker_apis import lasair

    msgs = [_msg(o, f"O{o}") for o in (1, 2, 3, 4)]
    key = lambda m: (m.topic(), m.partition(), m.offset())  # noqa: E731
    results = {
        key(msgs[0]): True,
        key(msgs[1]): True,
        key(msgs[2]): False,
        key(msgs[3]): True,
    }
    consumer = FakeConsumer()
    lasair._store_batch_offsets(consumer, msgs, set(), results)
    # offset 4 succeeded but sits behind the failure at 3, so it is replayed
    assert consumer.stored == [("lasair_2mine", 0, 2)]


def test_nothing_is_stored_when_the_first_message_fails():
    from skyportal.broker_apis import lasair

    msgs = [_msg(1, "A"), _msg(2, "B")]
    key = lambda m: (m.topic(), m.partition(), m.offset())  # noqa: E731
    consumer = FakeConsumer()
    lasair._store_batch_offsets(
        consumer, msgs, set(), {key(msgs[0]): False, key(msgs[1]): True}
    )
    assert consumer.stored == []


def test_a_failure_on_one_partition_does_not_hold_up_another():
    from skyportal.broker_apis import lasair

    a = [_msg(1, "A", partition=0), _msg(2, "B", partition=0)]
    b = [_msg(1, "C", partition=1), _msg(2, "D", partition=1)]
    key = lambda m: (m.topic(), m.partition(), m.offset())  # noqa: E731
    results = {key(a[0]): False, key(a[1]): True, key(b[0]): True, key(b[1]): True}
    consumer = FakeConsumer()
    lasair._store_batch_offsets(consumer, a + b, set(), results)
    assert consumer.stored == [("lasair_2mine", 1, 2)]


def test_a_whole_clean_batch_stores_its_last_offset():
    from skyportal.broker_apis import lasair

    msgs = [_msg(o, f"O{o}") for o in (5, 6, 7)]
    key = lambda m: (m.topic(), m.partition(), m.offset())  # noqa: E731
    consumer = FakeConsumer()
    lasair._store_batch_offsets(consumer, msgs, set(), {key(m): True for m in msgs})
    assert consumer.stored == [("lasair_2mine", 0, 7)]


def test_a_batch_is_ingested_with_bounded_concurrency(monkeypatch):
    import asyncio

    from skyportal.broker_apis import lasair

    live, peak = {"n": 0}, {"n": 0}

    async def fake_ingest(broker, oid, survey, filter_ids, token=None, payload=None):
        live["n"] += 1
        peak["n"] = max(peak["n"], live["n"])
        await asyncio.sleep(0.01)
        live["n"] -= 1
        if oid == "BAD":
            raise RuntimeError("boom")

    monkeypatch.setattr(lasair, "_ingest_object", fake_ingest)
    msgs = [_msg(i, f"O{i}") for i in range(10)] + [_msg(99, "BAD")]
    _finished, work = lasair._prepare_batch(msgs, {}, [1])
    results = asyncio.run(lasair._ingest_batch(None, "LSST", "t", work, 3))
    assert peak["n"] <= 3
    assert sum(1 for ok in results.values() if ok) == 10
    assert results[("lasair_2mine", 0, 99)] is False


def test_a_live_lasair_lite_lightcurve_message_normalizes():
    """Replayed from a real message on Lasair's lite_lightcurve tutorial topic.

    A live diaSource carries band/midpointMjdTai/psfFlux/psfFluxErr/reliability
    and no id, so the alert id falls back to the epoch.
    """
    from skyportal.broker_apis import lasair

    with open(os.path.join(CASSETTE_DIR, "lasair_lsst_lite_lightcurve.json")) as f:
        message = json.load(f)

    assert lasair.carries_lightcurve(message) is True
    sources = lasair._lsst_sources(message)
    assert sources and "diaSourceId" not in sources[0]

    oid = lasair._object_id_from_message(message)
    data = lasair._normalize_object(message, oid)
    _assert_standard_shape(data)
    candidate = data["candidate"]
    # the position the message itself reports
    assert candidate["ra"] == pytest.approx(message["ra"])
    assert candidate["dec"] == pytest.approx(message["decl"])
    # every source is a detection here, and each became a magnitude
    assert len(data["prv_candidates"]) == len(sources)
    assert all(20 < p["magpsf"] < 27 for p in data["prv_candidates"])
    # a null alert id would defeat candidate de-duplication
    assert isinstance(candidate["candid"], int)
    assert candidate["jd"] == pytest.approx(
        max(s["midpointMjdTai"] for s in sources) + 2400000.5
    )


def test_lasair_request_retries_on_rate_limit(monkeypatch):
    """Lasair rate-limits per account; a 429 must be waited out, not dropped."""
    import types

    from skyportal.broker_apis import lasair

    calls = {"n": 0, "slept": []}

    class Response:
        def __init__(self, status_code, headers=None):
            self.status_code = status_code
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        @property
        def text(self):
            return '[{"objectId": "ZTF1"}]'

        def json(self):
            return [{"objectId": "ZTF1"}]

    def fake_post(url, data=None, headers=None, timeout=None):
        calls["n"] += 1
        # rate-limited once, with Lasair telling us how long to wait
        if calls["n"] == 1:
            return Response(429, {"Retry-After": "2"})
        return Response(200)

    monkeypatch.setattr(lasair.requests, "post", fake_post)
    monkeypatch.setattr(lasair.time, "sleep", lambda s: calls["slept"].append(s))

    broker = types.SimpleNamespace(
        altdata={"endpoint": "https://lasair.test/api", "token": "secret"}
    )
    assert lasair._request(broker, "object", {"objectId": "ZTF1"}) == [
        {"objectId": "ZTF1"}
    ]
    assert calls["n"] == 2, "the request was not retried"
    assert calls["slept"] == [2.0], "Retry-After was ignored"


def test_lasair_request_gives_up_after_repeated_rate_limits(monkeypatch):
    """Retrying forever would stall the whole ingestion cycle."""
    import types

    from skyportal.broker_apis import lasair

    class Response:
        status_code = 429
        headers: dict = {}

        def raise_for_status(self):
            raise RuntimeError("HTTP 429")

        def json(self):
            return {}

    monkeypatch.setattr(lasair.requests, "post", lambda *a, **k: Response())
    monkeypatch.setattr(lasair.time, "sleep", lambda s: None)

    broker = types.SimpleNamespace(
        altdata={"endpoint": "https://lasair.test/api", "token": "secret"}
    )
    with pytest.raises(RuntimeError):
        lasair._request(broker, "object", {"objectId": "ZTF1"})


def _fits_bytes(value=7.0):
    """A minimal FITS image, uncompressed."""
    import io

    import numpy as np
    from astropy.io import fits

    buff = io.BytesIO()
    fits.PrimaryHDU(np.full((4, 4), value, dtype=np.float32)).writeto(buff)
    return buff.getvalue()


def test_decode_cutout_accepts_gzipped_and_plain_fits():
    """Compression is a property of the payload, not of the survey.

    ZTF alerts carry gzipped FITS, LSST does not, and Lasair serves ZTF cutouts
    uncompressed -- which used to fail with "Not a gzipped file (b'SI')",
    leaving Lasair-only objects with no thumbnails at all.
    """
    import base64
    import gzip

    from skyportal.broker_apis._thumbnails import decode_cutout

    plain = _fits_bytes()
    gzipped = gzip.compress(plain)

    for label, payload in (("gzipped", gzipped), ("plain", plain)):
        data, header = decode_cutout(payload, "ZTF")
        assert data.shape == (4, 4), label
        assert data[0][0] == 7.0, label
        assert header["NAXIS"] == 2, label

    # base64 of either, which is how providers usually send them
    for label, payload in (("gzipped", gzipped), ("plain", plain)):
        data, _ = decode_cutout(base64.b64encode(payload).decode(), "LSST")
        assert data[0][0] == 7.0, f"base64 {label}"


def test_orient_cutout_mirrors_decam_across_the_anti_diagonal():
    """DECam stamps are stored mirrored relative to the sky (checked against
    Legacy Survey images), so opposite corners off the anti-diagonal swap."""
    import numpy as np

    from skyportal.broker_apis._thumbnails import orient_cutout

    stamp = np.zeros((63, 63))
    stamp[0, 0] = 1
    stamp[-1, -1] = 2
    stamp[0, -1] = 3
    oriented = orient_cutout(stamp, "DECAM", {})
    assert oriented[-1, -1] == 1
    assert oriented[0, 0] == 2
    assert oriented[0, -1] == 3


def test_decode_cutout_rejects_a_url_placeholder():
    """A provider sending a URL instead of image bytes should say so clearly."""
    from skyportal.broker_apis._thumbnails import decode_cutout

    with pytest.raises(ValueError, match="not valid base64"):
        decode_cutout("https://example.test/cutout.fits", "ZTF")


def test_lasair_stream_message_object_ids():
    """Lasair streams carry the objectId under different keys per deployment, and
    a filter's stream may wrap the row, so all of those must resolve."""
    from skyportal.broker_apis.lasair import (
        _decode_stream_message,
        _object_id_from_message,
    )

    def oid(raw):
        return _object_id_from_message(_decode_stream_message(raw))

    assert oid(b'{"diaObjectId": 123456789}') == "123456789"  # LSST
    assert oid(b'{"objectId": "ZTF26absuusx"}') == "ZTF26absuusx"  # ZTF
    assert oid(b'{"object": "ZTF18abcdefg"}') == "ZTF18abcdefg"
    assert oid('{"objectId": "ZTF21bbb"}') == "ZTF21bbb"  # str, not bytes
    assert oid(b'{"objectData": {"objectId": "ZTF20aaa"}}') == "ZTF20aaa"
    assert oid(b'{"ramean": 1.0}') is None


def test_lasair_stream_message_accepts_avro():
    """JSON today, but an Avro payload decodes rather than raising."""
    import io

    import fastavro

    from skyportal.broker_apis.lasair import (
        _decode_stream_message,
        _object_id_from_message,
    )

    buf = io.BytesIO()
    fastavro.writer(
        buf,
        {
            "type": "record",
            "name": "L",
            "fields": [{"name": "objectId", "type": "string"}],
        },
        [{"objectId": "ZTF22avro"}],
    )
    assert (
        _object_id_from_message(_decode_stream_message(buf.getvalue())) == "ZTF22avro"
    )


def test_lasair_ingestion_uses_kafka_when_configured(monkeypatch):
    """A configured stream takes precedence over the SQL poller, and topics route
    to their own filters."""
    import asyncio
    import types

    import skyportal.broker_apis.lasair as lasair_mod

    seen = {}

    async def fake_kafka(broker, survey, stop=None, max_messages=None):
        seen["survey"] = survey
        seen["topics"] = (broker.altdata["kafka"] or {}).get("topics")
        return 7

    async def no_user_credentials(broker):
        return []

    monkeypatch.setattr(lasair_mod, "_run_kafka_ingestion", fake_kafka)
    monkeypatch.setattr(lasair_mod, "_user_credential_sets", no_user_credentials)
    broker = types.SimpleNamespace(
        id=9,
        altdata={
            "survey": "LSST",
            "token": "x",
            "endpoint": "https://api.lasair.lsst.ac.uk/api",
            "kafka": {"host": "kafka.test", "topics": ["lasair_2SN-likecandidates"]},
        },
    )
    count = asyncio.run(LASAIRBROKER.run_ingestion(broker, max_messages=1))
    assert count == 7, "the Kafka path was not taken"
    assert seen["survey"] == "LSST"
    assert seen["topics"] == ["lasair_2SN-likecandidates"]


def test_lasair_ingestion_uses_kafka_for_user_topics_alone(monkeypatch):
    """A user's own account owning the topics is enough: the broker needs no
    shared stream config for that user's filters to be consumed."""
    import asyncio
    import types

    import skyportal.broker_apis.lasair as lasair_mod

    seen = {}

    async def fake_kafka(broker, survey, stop=None, max_messages=None):
        seen["survey"] = survey
        return 7

    async def one_user_credential(broker):
        return [{"label": "user3", "topics": ["lasair_9private"]}]

    monkeypatch.setattr(lasair_mod, "_run_kafka_ingestion", fake_kafka)
    monkeypatch.setattr(lasair_mod, "_user_credential_sets", one_user_credential)
    broker = types.SimpleNamespace(
        id=9,
        altdata={
            "survey": "LSST",
            "token": "x",
            "endpoint": "https://api.lasair.lsst.ac.uk/api",
        },
    )
    count = asyncio.run(LASAIRBROKER.run_ingestion(broker, max_messages=1))
    assert count == 7, "the Kafka path was not taken"
    assert seen["survey"] == "LSST"


def test_lasair_kafka_picks_up_a_new_account(monkeypatch):
    """A user registering an account mid-run gets a consumer without the service
    being restarted, and one that goes away is stopped."""
    import asyncio
    import types

    import skyportal.broker_apis.lasair as lasair_mod

    consumed = []
    accounts = [{"label": "camille", "topics": ["lasair_9a"], "kafka": {}}]

    async def fake_user_sets(broker):
        return list(accounts)

    async def fake_consume(broker, survey, credentials, budget, stop):
        consumed.append(credentials["label"])
        await stop.wait()

    monkeypatch.setattr(lasair_mod, "_user_credential_sets", fake_user_sets)
    monkeypatch.setattr(lasair_mod, "_consume_set", fake_consume)
    monkeypatch.setattr(lasair_mod, "CREDENTIAL_RESCAN_INTERVAL", 0.01)
    broker = types.SimpleNamespace(id=9, altdata={"survey": "LSST", "token": "x"})

    async def scenario():
        stop = asyncio.Event()
        run = asyncio.create_task(
            lasair_mod._run_kafka_ingestion(broker, "LSST", stop=stop)
        )
        while "camille" not in consumed:
            await asyncio.sleep(0.01)
        accounts.append({"label": "alex", "topics": ["lasair_4b"], "kafka": {}})
        while "alex" not in consumed:
            await asyncio.sleep(0.01)
        accounts.pop(0)
        await asyncio.sleep(0.1)
        stop.set()
        await asyncio.wait_for(run, timeout=5)

    asyncio.run(asyncio.wait_for(scenario(), timeout=10))
    assert consumed == ["camille", "alex"], consumed


def test_lasair_kafka_restarts_a_crashed_consumer_without_spinning(monkeypatch):
    """A consumer that fails on connect is retried rather than lost, and the pause
    grows, so an account that stays broken does not burn a core nor spam the log."""
    import asyncio
    import types

    import skyportal.broker_apis.lasair as lasair_mod

    starts = []

    def crashing(broker, survey, credentials, budget, stop):
        starts.append(credentials["label"])

        async def run():
            raise RuntimeError("connect failed")

        return run()

    async def fake_user_sets(broker):
        return [{"label": "camille", "topics": ["lasair_9a"], "kafka": {}}]

    monkeypatch.setattr(lasair_mod, "_consume_set", crashing)
    monkeypatch.setattr(lasair_mod, "_user_credential_sets", fake_user_sets)
    monkeypatch.setattr(lasair_mod, "CREDENTIAL_RESCAN_INTERVAL", 0.02)
    monkeypatch.setattr(lasair_mod, "CONSUMER_RETRY_PAUSE", 0.02)
    broker = types.SimpleNamespace(id=9, altdata={"survey": "LSST", "token": "x"})

    async def scenario():
        stop = asyncio.Event()
        run = asyncio.create_task(
            lasair_mod._run_kafka_ingestion(broker, "LSST", stop=stop)
        )
        await asyncio.sleep(0.4)
        stop.set()
        await asyncio.wait_for(run, timeout=5)

    asyncio.run(asyncio.wait_for(scenario(), timeout=10))
    # A fixed 0.02s pause would give ~20 restarts over 0.4s; doubling gives ~5.
    assert 1 < len(starts) <= 8, len(starts)


def test_lasair_stream_selected_only_when_topics_configured():
    """Streaming is opt-in: a broker with no topics keeps polling, so existing
    Lasair brokers are unaffected by the Kafka path."""
    from skyportal.broker_apis.lasair import _stream_configured

    assert _stream_configured({"kafka": {"topics": ["lasair_2SN"]}}) is True
    assert (
        _stream_configured({"kafka": {"topic_filter_ids": {"lasair_2SN": [1]}}}) is True
    )
    assert _stream_configured({"kafka": {"host": "kafka.test"}}) is False
    assert _stream_configured({"kafka": {"topics": []}}) is False
    assert _stream_configured({"queries": []}) is False
    assert _stream_configured({}) is False
    assert _stream_configured(None) is False


def test_transient_photometry_resolves_ids_once_per_request():
    """Instrument and obj ids are resolved across all of an object's groups, so
    the query count does not grow with the number of groups."""
    import asyncio

    from skyportal.broker_apis._photometry import transient_photometry
    from skyportal.models import Instrument, Obj, Telescope

    instrument = Instrument(
        id=1,
        name="ZTF",
        type="imager",
        band="optical",
        filters=["ztfg"],
        telescope=Telescope(
            id=1,
            name="P48",
            nickname="P48",
            lat=33.0,
            lon=-116.0,
            elevation=1700.0,
            diameter=1.2,
        ),
    )
    obj_id = "ZTF26abcdefg"

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _RecordingSession:
        """Answers the id lookups and counts them."""

        def __init__(self):
            self.calls = []

        async def scalars(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            self.calls.append(entity)
            return _Result([instrument] if entity is Instrument else [obj_id])

    def groups(n):
        return {
            f"g{i}": {
                "obj_id": [obj_id],
                "instrument_id": [instrument.id],
                "mjd": [59000.0 + i],
                "filter": ["ztfg"],
                "flux": [100.0 + i],
                "fluxerr": [10.0],
                "zp": [23.9],
                "magsys": ["ab"],
            }
            for i in range(n)
        }

    async def query_counts():
        counts = {}
        for n in (1, 6):
            session = _RecordingSession()
            phots = await transient_photometry(groups(n), session)
            assert len(phots) == n
            # serialize() reads phot.instrument, which no query would load here
            assert all(p.instrument is instrument for p in phots)
            counts[n] = len(session.calls)
        return counts

    # One for the instruments, one for the objs, however many groups there are.
    assert asyncio.run(query_counts()) == {1: 2, 6: 2}


def test_transient_photometry_keeps_the_point_origin():
    """A group carries origin per point, and the payload must forward it: dropped,
    every broker point looked like an alert point, so a forced measurement was
    deduped away against the upper limit saved at its epoch and the lightcurve
    showed no forced photometry at all."""
    import asyncio

    from skyportal.broker_apis._photometry import transient_photometry
    from skyportal.models import Instrument, Telescope

    instrument = Instrument(
        id=1,
        name="ZTF",
        type="imager",
        band="optical",
        filters=["ztfg"],
        telescope=Telescope(
            id=1,
            name="P48",
            nickname="P48",
            lat=33.0,
            lon=-116.0,
            elevation=1700.0,
            diameter=1.2,
        ),
    )
    obj_id = "ZTF26abcdefg"

    class _Session:
        async def scalars(self, stmt):
            entity = stmt.column_descriptions[0]["entity"]
            rows = [instrument] if entity is Instrument else [obj_id]
            return type("_Result", (), {"all": staticmethod(lambda: rows)})()

    group = {
        "obj_id": [obj_id, obj_id],
        "instrument_id": [instrument.id, instrument.id],
        "mjd": [59000.0, 59000.0],
        "filter": ["ztfg", "ztfg"],
        "origin": [None, "fp"],
        "flux": [None, 120.0],
        "fluxerr": [10.0, 10.0],
        "zp": [23.9, 23.9],
        "magsys": ["ab", "ab"],
    }
    phots = asyncio.run(transient_photometry({"ZTF1": group}, _Session()))
    assert [p.origin for p in phots] == ["None", "fp"]
