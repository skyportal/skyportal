import base64

import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/alerce")

# ALeRCE's public (no-auth) REST APIs. ZTF and LSST live on distinct hosts with
# different schemas: ZTF is mag-space (api.alerce.online/ztf/v1); LSST is the
# flux-space multisurvey API (api-lsst.alerce.online, ?survey_id=lsst).
DEFAULT_API_URL = "https://api.alerce.online/ztf/v1"
DEFAULT_STAMP_URL = "https://avro.alerce.online"
DEFAULT_LSST_API_URL = "https://api-lsst.alerce.online"
DEFAULT_LSST_STAMP_URL = "https://api-lsst.alerce.online/stamps_api"
DEFAULT_TIMEOUT = 30  # seconds
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


def _survey(broker):
    return ((broker.altdata or {}).get("survey") or "ZTF").upper()


def _api_url(broker):
    return (broker.altdata or {}).get("api_url", DEFAULT_API_URL)


def _stamp_url(broker):
    return (broker.altdata or {}).get("stamp_url", DEFAULT_STAMP_URL)


def _get(broker, path, params=None):
    url = f"{_api_url(broker).rstrip('/')}/{path.lstrip('/')}"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _lsst_api_url(broker):
    return (broker.altdata or {}).get("lsst_api_url", DEFAULT_LSST_API_URL)


def _lsst_stamp_url(broker):
    return (broker.altdata or {}).get("lsst_stamp_url", DEFAULT_LSST_STAMP_URL)


def _lsst_get(broker, path, params=None):
    url = f"{_lsst_api_url(broker).rstrip('/')}/{path.lstrip('/')}"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _first(obj):
    """Unwrap ALeRCE object responses that may be a bare dict, a {items:[...]}
    envelope, or a list."""
    if isinstance(obj, dict):
        if "items" in obj:
            items = obj.get("items") or []
            return items[0] if items else {}
        return obj
    if isinstance(obj, list):
        return obj[0] if obj else {}
    return {}


def _band_name(d):
    # LSST detections carry a per-message band_map ({str(int): letter}); the
    # client resolves band_name from it. Fall back to any provided band_name.
    band_map = d.get("band_map") or {}
    return band_map.get(str(d.get("band"))) or d.get("band_name")


def _cone_params(ra, dec, kwargs=None):
    # The list endpoint is /objects/ (trailing slash avoids a 301 that can hang);
    # count=false skips ALeRCE's slow total-count query.
    kwargs = kwargs or {}
    return {
        "ra": ra,
        "dec": dec,
        "radius": kwargs.get("radius", 5),
        "page": 1,
        "page_size": kwargs.get("limit", 20),
        "count": "false",
    }


def _mag(d):
    return d.get("magpsf") if d.get("magpsf") is not None else d.get("mag")


def _magerr(d):
    return d.get("sigmapsf") if d.get("sigmapsf") is not None else d.get("e_mag")


def _normalize_object(object_id, meta, detections):
    """Reshape ALeRCE object metadata + detections (mag-space, mjd) into the
    standard {objectId, candidate, prv_candidates} shape."""
    meta = meta or {}
    dets = [d for d in (detections or []) if _mag(d) is not None]
    dets.sort(key=lambda d: d.get("mjd") or 0)
    latest = dets[-1] if dets else {}
    prv = [
        {
            "jd": (d.get("mjd") + 2400000.5) if d.get("mjd") is not None else None,
            "magpsf": _mag(d),
            "sigmapsf": _magerr(d),
            "band": _FID_TO_BAND.get(d.get("fid")),
            "ra": d.get("ra"),
            "dec": d.get("dec"),
        }
        for d in dets
    ]
    return {
        "objectId": object_id,
        "candidate": {
            "ra": meta.get("meanra") or latest.get("ra"),
            "dec": meta.get("meandec") or latest.get("dec"),
            "magpsf": _mag(latest),
            "jd": (latest.get("mjd") + 2400000.5)
            if latest.get("mjd") is not None
            else None,
            "band": _FID_TO_BAND.get(latest.get("fid")),
        },
        "prv_candidates": prv,
    }


def _normalize_lsst_object(object_id, meta, detections):
    """Reshape ALeRCE multisurvey LSST object metadata + detections (flux-space,
    psfFlux in nJy, mjd) into the standard {objectId, candidate, prv_candidates}
    shape."""
    meta = meta or {}
    dets = [d for d in (detections or []) if d.get("psfFlux") is not None]
    dets.sort(key=lambda d: d.get("mjd") or 0)
    latest = dets[-1] if dets else {}
    prv = [
        {
            "jd": (d.get("mjd") + 2400000.5) if d.get("mjd") is not None else None,
            "psfFlux": d.get("psfFlux"),
            "psfFluxErr": d.get("psfFluxErr"),
            "band": _band_name(d),
            "ra": d.get("ra"),
            "dec": d.get("dec"),
        }
        for d in dets
    ]
    return {
        "objectId": str(object_id),
        "candidate": {
            "ra": meta.get("meanra") or latest.get("ra"),
            "dec": meta.get("meandec") or latest.get("dec"),
            "psfFlux": latest.get("psfFlux"),
            "psfFluxErr": latest.get("psfFluxErr"),
            "jd": (latest.get("mjd") + 2400000.5)
            if latest.get("mjd") is not None
            else None,
            "band": _band_name(latest),
        },
        "prv_candidates": prv,
    }


class ALERCEBROKER(BrokerAPI):
    """The ALeRCE broker (https://alerce.science).

    Interactive access to ALeRCE's public (no-auth) REST APIs. ZTF: object
    metadata + detections (mag-space) at ``api.alerce.online/ztf/v1`` and stamps
    (gzipped FITS) at ``avro.alerce.online``. LSST: the flux-space multisurvey
    API at ``api-lsst.alerce.online`` (?survey_id=lsst) with FITS stamps at
    ``.../stamps_api``. Select the survey via ``altdata['survey']`` (ZTF/LSST).
    """

    surveys = ["ZTF", "LSST"]

    form_json_schema_config = {
        "type": "object",
        "properties": {
            "api_url": {
                "type": "string",
                "title": "ZTF REST API URL",
                "default": DEFAULT_API_URL,
            },
            "stamp_url": {
                "type": "string",
                "title": "ZTF Stamp API URL",
                "default": DEFAULT_STAMP_URL,
            },
            "lsst_api_url": {
                "type": "string",
                "title": "LSST REST API URL",
                "default": DEFAULT_LSST_API_URL,
            },
            "lsst_stamp_url": {
                "type": "string",
                "title": "LSST Stamp API URL",
                "default": DEFAULT_LSST_STAMP_URL,
            },
            "survey": {
                "type": "string",
                "enum": ["ZTF", "LSST"],
                "default": "ZTF",
            },
        },
    }

    @staticmethod
    def validate_config(altdata):
        # No credentials required; ALeRCE's REST APIs are public.
        return

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return [ALERCEBROKER.get_alert(broker, object_id, session, **kwargs)]
        ra, dec = kwargs.get("ra"), kwargs.get("dec")
        if ra is None or dec is None:
            raise ValueError("Provide objectId, or ra+dec.")
        if _survey(broker) == "LSST":
            result = _lsst_get(
                broker,
                "object_api/list_objects",
                {
                    "survey": "lsst",
                    "ra": ra,
                    "dec": dec,
                    "radius": kwargs.get("radius", 5),
                    "page": 1,
                    "page_size": kwargs.get("limit", 20),
                },
            )
            items = result.get("items", []) if isinstance(result, dict) else result
            return [_normalize_lsst_object(o.get("oid"), o, []) for o in (items or [])]
        result = _get(broker, "objects/", params=_cone_params(ra, dec, kwargs))
        items = result.get("items", []) if isinstance(result, dict) else result
        return [_normalize_object(o.get("oid"), o, []) for o in (items or [])]

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        if _survey(broker) == "LSST":
            meta = {}
            try:
                meta = _first(
                    _lsst_get(
                        broker,
                        "object_api/object",
                        {"survey_id": "lsst", "oid": alert_id},
                    )
                )
            except Exception:
                meta = {}
            detections = _lsst_get(
                broker,
                "lightcurve_api/detections",
                {"survey_id": "lsst", "oid": alert_id},
            )
            if isinstance(detections, dict):
                detections = detections.get("items") or detections.get("detections")
            return _normalize_lsst_object(alert_id, meta, detections)
        meta = {}
        try:
            meta = _get(broker, f"objects/{alert_id}")
        except Exception:
            meta = {}
        detections = _get(broker, f"objects/{alert_id}/detections")
        return _normalize_object(alert_id, meta, detections)

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        if _survey(broker) == "LSST":
            return _lsst_get(
                broker,
                "object_api/list_objects",
                {
                    "survey": "lsst",
                    "ra": ra,
                    "dec": dec,
                    "radius": radius,
                    "page": 1,
                    "page_size": 20,
                },
            )
        return _get(
            broker, "objects/", params=_cone_params(ra, dec, {"radius": radius})
        )

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        """Fetch science/template/difference stamps (FITS) for an object.
        ``alert_id`` is the objectId; a detection's candid (ZTF) / measurement_id
        (LSST) keys the stamp. Returns base64 FITS the frontend decodes like any
        other broker."""
        if _survey(broker) == "LSST":
            detections = _lsst_get(
                broker,
                "lightcurve_api/detections",
                {"survey_id": "lsst", "oid": alert_id},
            )
            dets = [
                d
                for d in (detections or [])
                if d.get("has_stamp") and d.get("measurement_id")
            ]
            if not dets:
                return {}
            dets.sort(key=lambda d: d.get("mjd") or 0)
            measurement_id = dets[0]["measurement_id"]  # earliest with a stamp
            stamp_base = _lsst_stamp_url(broker).rstrip("/")
            cutouts = {}
            for stamp_type, field in (
                ("Science", "cutoutScience"),
                ("Template", "cutoutTemplate"),
                ("Difference", "cutoutDifference"),
            ):
                try:
                    response = requests.get(
                        f"{stamp_base}/stamp",
                        params={
                            "oid": alert_id,
                            "measurement_id": measurement_id,
                            "stamp_type": stamp_type,
                            "file_format": "fits",
                            "survey_id": "lsst",
                        },
                        timeout=DEFAULT_TIMEOUT,
                    )
                    response.raise_for_status()
                    cutouts[field] = base64.b64encode(response.content).decode("utf-8")
                except Exception as e:
                    log(f"ALeRCE LSST {stamp_type} stamp failed for {alert_id}: {e}")
            return cutouts
        detections = _get(broker, f"objects/{alert_id}/detections")
        dets = [d for d in (detections or []) if d.get("candid")]
        if not dets:
            return {}
        dets.sort(key=lambda d: d.get("mjd") or 0)
        candid = dets[-1]["candid"]
        stamp_base = _stamp_url(broker).rstrip("/")
        cutouts = {}
        for stamp_type, field in (
            ("science", "cutoutScience"),
            ("template", "cutoutTemplate"),
            ("difference", "cutoutDifference"),
        ):
            try:
                response = requests.get(
                    f"{stamp_base}/get_stamp",
                    params={
                        "oid": alert_id,
                        "candid": candid,
                        "type": stamp_type,
                        "format": "fits",
                    },
                    timeout=DEFAULT_TIMEOUT,
                )
                response.raise_for_status()
                cutouts[field] = base64.b64encode(response.content).decode("utf-8")
            except Exception as e:
                log(f"ALeRCE {stamp_type} stamp failed for {alert_id}: {e}")
        return cutouts

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Poll ALeRCE (no public Kafka firehose): run each configured ``/objects``
        query, and for every returned object fetch its light curve via ``get_alert``
        and register a Candidate under ``filter_ids``. Config in ``broker.altdata``:
        ``queries`` (list of /objects param dicts, e.g. {"class_name","probability",
        "ndet","firstmjd"}), ``filter_ids``, ``survey``, ``poll_interval``,
        ``page_size``."""
        import asyncio

        import sqlalchemy as sa

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        survey = altdata.get("survey", "ZTF")
        is_lsst = survey.upper() == "LSST"
        filter_ids = altdata.get("filter_ids") or []
        # Default: the most-recently-active objects (users add class/ndet filters).
        queries = altdata.get("queries") or [
            {"order_by": "lastmjd", "order_mode": "DESC"}
        ]
        poll_interval = float(altdata.get("poll_interval", 3600))
        page_size = int(altdata.get("page_size", 100))

        def _stopped():
            return stop is not None and stop.is_set()

        count = 0
        while not _stopped():
            for query in queries:
                try:
                    if is_lsst:
                        params = {**query, "survey": "lsst", "page_size": page_size}
                        result = await asyncio.to_thread(
                            _lsst_get, broker, "object_api/list_objects", params
                        )
                    else:
                        params = {**query, "page_size": page_size, "count": "false"}
                        result = await asyncio.to_thread(
                            _get, broker, "objects/", params
                        )
                except Exception as e:
                    log(f"ALeRCE query failed: {e}")
                    continue
                items = (
                    result.get("items", [])
                    if isinstance(result, dict)
                    else (result or [])
                )
                for o in items:
                    if _stopped():
                        break
                    oid = o.get("oid")
                    if not oid:
                        continue
                    try:
                        data = await asyncio.to_thread(
                            ALERCEBROKER.get_alert, broker, oid, None
                        )
                        async with async_plain_session_factory() as session:
                            user = await session.scalar(
                                sa.select(User).where(User.id == 1)
                            )
                            await save_object_as_candidate(
                                data, survey, session, user, filter_ids
                            )
                    except Exception as e:
                        log(f"Error ingesting ALeRCE object {oid}: {e}")
                    count += 1
                    if max_messages is not None and count >= max_messages:
                        log(
                            f"ALeRCE ingestion (broker {broker.id}): "
                            f"ingested {count} objects"
                        )
                        return count
            if max_messages is not None:
                break  # bounded mode: a single pass
            slept = 0.0
            while slept < poll_interval and not _stopped():
                await asyncio.sleep(min(5.0, poll_interval - slept))
                slept += 5.0
        log(f"ALeRCE ingestion (broker {broker.id}): ingested {count} objects")
        return count
