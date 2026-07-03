import base64

import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/alerce")

# ALeRCE's public (no-auth) REST APIs.
DEFAULT_API_URL = "https://api.alerce.online/ztf/v1"
DEFAULT_STAMP_URL = "https://avro.alerce.online"
DEFAULT_TIMEOUT = 30  # seconds
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


def _api_url(broker):
    return (broker.altdata or {}).get("api_url", DEFAULT_API_URL)


def _stamp_url(broker):
    return (broker.altdata or {}).get("stamp_url", DEFAULT_STAMP_URL)


def _get(broker, path, params=None):
    url = f"{_api_url(broker).rstrip('/')}/{path.lstrip('/')}"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


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


class ALERCEBROKER(BrokerAPI):
    """The ALeRCE broker (https://alerce.science, ZTF alerts).

    Interactive access to ALeRCE's public (no-auth) REST APIs: object metadata +
    detections (light curve) at ``api.alerce.online/ztf/v1`` and science/template/
    difference stamps (gzipped FITS) at ``avro.alerce.online``. Configure a
    ``Broker`` with an empty ``altdata`` (or override ``api_url``/``stamp_url``).
    """

    surveys = ["ZTF"]

    form_json_schema_config = {
        "type": "object",
        "properties": {
            "api_url": {
                "type": "string",
                "title": "REST API URL",
                "default": DEFAULT_API_URL,
            },
            "stamp_url": {
                "type": "string",
                "title": "Stamp API URL",
                "default": DEFAULT_STAMP_URL,
            },
            "survey": {
                "type": "string",
                "enum": ["ZTF"],
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
        if ra is not None and dec is not None:
            result = _get(broker, "objects/", params=_cone_params(ra, dec, kwargs))
            items = result.get("items", []) if isinstance(result, dict) else result
            return [_normalize_object(o.get("oid"), o, []) for o in (items or [])]
        raise ValueError("Provide objectId, or ra+dec.")

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        meta = {}
        try:
            meta = _get(broker, f"objects/{alert_id}")
        except Exception:
            meta = {}
        detections = _get(broker, f"objects/{alert_id}/detections")
        return _normalize_object(alert_id, meta, detections)

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        return _get(
            broker, "objects/", params=_cone_params(ra, dec, {"radius": radius})
        )

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        """Fetch science/template/difference stamps (gzipped FITS) for an object.
        ``alert_id`` is the objectId; the latest detection's candid keys the
        stamp. Returns base64 FITS the frontend decodes like any other broker."""
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
                params = {**query, "page_size": page_size, "count": "false"}
                try:
                    result = await asyncio.to_thread(_get, broker, "objects/", params)
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
