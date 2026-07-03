import base64
import json

import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/antares")

# ANTARES ZTF alerts use fid (1=g, 2=R); the client exposes ant_passband too.
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}
DEFAULT_LIMIT = 20
# ANTARES' public (no-auth) JSON:API REST endpoint (the antares-client wraps this;
# we hit it directly to avoid the dependency).
DEFAULT_API_URL = "https://api.antares.noirlab.edu/v1/"
DEFAULT_TIMEOUT = 60  # seconds


def _survey(broker):
    return ((broker.altdata or {}).get("survey") or "ZTF").upper()


def _api_url(broker):
    return (broker.altdata or {}).get("api_url", DEFAULT_API_URL)


def _get(broker, path, params=None):
    url = _api_url(broker).rstrip("/") + "/" + path.lstrip("/")
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _get_url(url):
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


class _Alert:
    """Lightweight stand-in for an antares_client Alert (JSON:API id ->
    alert_id, plus mjd/properties from attributes)."""

    def __init__(self, alert_id, mjd, properties):
        self.alert_id = alert_id
        self.mjd = mjd
        self.properties = properties or {}


class _Locus:
    """Lightweight stand-in for an antares_client Locus consumed by the
    normalizers (locus_id/ra/dec/properties/alerts)."""

    def __init__(self, locus_id, ra, dec, properties, alerts):
        self.locus_id = locus_id
        self.ra = ra
        self.dec = dec
        self.properties = properties or {}
        self.alerts = alerts


def _fetch_alerts(broker, locus_id):
    """All alerts for a locus (JSON:API, following pagination)."""
    alerts = []
    result = _get(broker, f"loci/{locus_id}/alerts")
    while result:
        for item in result.get("data", []):
            attrs = item.get("attributes", {}) or {}
            alerts.append(
                _Alert(item.get("id"), attrs.get("mjd"), attrs.get("properties"))
            )
        nxt = (result.get("links") or {}).get("next")
        if not nxt:
            break
        result = _get_url(nxt)
    return alerts


def _locus_from_item(broker, item):
    attrs = item.get("attributes", {}) or {}
    return _Locus(
        item.get("id"),
        attrs.get("ra"),
        attrs.get("dec"),
        attrs.get("properties"),
        _fetch_alerts(broker, item.get("id")),
    )


def _search_loci(broker, es_query, limit):
    """Build loci matching an Elasticsearch query (most-recently-updated first)."""
    params = {
        "sort": "-properties.newest_alert_observation_time",
        "elasticsearch_query[locus_listing]": json.dumps(es_query),
    }
    result = _get(broker, "loci", params)
    out = []
    while result:
        for item in result.get("data", []):
            out.append(_locus_from_item(broker, item))
            if len(out) >= limit:
                return out
        nxt = (result.get("links") or {}).get("next")
        if not nxt:
            break
        result = _get_url(nxt)
    return out


def _cone_query(ra, dec, radius_arcsec):
    return {
        "query": {
            "bool": {
                "filter": {
                    "sky_distance": {
                        "distance": f"{float(radius_arcsec) / 3600.0} degree",
                        "htm16": {"center": f"{float(ra)} {float(dec)}"},
                    }
                }
            }
        }
    }


def _locus(broker, alert_id, survey="ZTF"):
    """Fetch a locus by ZTF objectId / LSST diaObjectId / ANTARES locus id."""
    if survey == "LSST":
        field = "properties.survey.lsst.dia_object_id"
        loci = _search_loci(
            broker, {"query": {"bool": {"filter": {"term": {field: str(alert_id)}}}}}, 1
        )
        if loci:
            return loci[0]
    elif str(alert_id).startswith("ZTF"):
        field = "properties.ztf_object_id"
        loci = _search_loci(
            broker, {"query": {"bool": {"filter": {"term": {field: alert_id}}}}}, 1
        )
        if loci:
            return loci[0]
    # fall back to a direct ANTARES locus-id lookup
    detail = _get(broker, f"loci/{alert_id}")
    if detail and detail.get("data"):
        return _locus_from_item(broker, detail["data"])
    return None


def _lsst_object_id(locus):
    props = getattr(locus, "properties", {}) or {}
    ids = ((props.get("survey") or {}).get("lsst") or {}).get("dia_object_id") or []
    return str(ids[0]) if ids else None


def _normalize_lsst_locus(locus):
    """Reshape a Locus's LSST alerts (``lsst_diaSource_*`` properties, flux-space
    psfFlux in nJy, midpointMjdTai) into the standard {objectId, candidate,
    prv_candidates} shape. A locus may also carry cross-matched ZTF alerts; those
    (no ``lsst_diaSource_psfFlux``) are skipped here."""
    prv = []
    for alert in getattr(locus, "alerts", None) or []:
        p = alert.properties or {}
        flux = p.get("lsst_diaSource_psfFlux")
        mjd = p.get("lsst_diaSource_midpointMjdTai")
        if flux is None or mjd is None:
            continue
        prv.append(
            {
                "jd": mjd + 2400000.5,
                "psfFlux": flux,
                "psfFluxErr": p.get("lsst_diaSource_psfFluxErr"),
                "band": p.get("lsst_diaSource_band"),
                "ra": p.get("lsst_diaSource_ra"),
                "dec": p.get("lsst_diaSource_dec"),
            }
        )
    prv.sort(key=lambda d: d["jd"] or 0)
    latest = prv[-1] if prv else {}
    return {
        "objectId": _lsst_object_id(locus) or getattr(locus, "locus_id", None),
        "candidate": {
            "ra": getattr(locus, "ra", None) or latest.get("ra"),
            "dec": getattr(locus, "dec", None) or latest.get("dec"),
            "psfFlux": latest.get("psfFlux"),
            "psfFluxErr": latest.get("psfFluxErr"),
            "jd": latest.get("jd"),
            "band": latest.get("band"),
        },
        "prv_candidates": prv,
    }


def _normalize(locus, survey):
    return _normalize_lsst_locus(locus) if survey == "LSST" else _normalize_locus(locus)


def _normalize_locus(locus):
    """Reshape an ANTARES Locus (alerts carry ant_mjd/ant_mag/ant_magerr/ztf_fid)
    into the standard {objectId, candidate, prv_candidates} shape."""
    props = getattr(locus, "properties", {}) or {}
    object_id = props.get("ztf_object_id") or getattr(locus, "locus_id", None)
    prv = []
    for alert in getattr(locus, "alerts", None) or []:
        p = alert.properties or {}
        if p.get("ant_mag") is None:  # skip non-detections (upper limits)
            continue
        mjd = p.get("ant_mjd")
        prv.append(
            {
                "jd": (mjd + 2400000.5) if mjd is not None else None,
                "magpsf": p.get("ant_mag"),
                "sigmapsf": p.get("ant_magerr"),
                "band": _FID_TO_BAND.get(p.get("ztf_fid")),
                "ra": p.get("ant_ra"),
                "dec": p.get("ant_dec"),
            }
        )
    prv.sort(key=lambda d: d["jd"] or 0)
    latest = prv[-1] if prv else {}
    return {
        "objectId": object_id,
        "candidate": {
            "ra": getattr(locus, "ra", None),
            "dec": getattr(locus, "dec", None),
            "magpsf": latest.get("magpsf"),
            "jd": latest.get("jd"),
            "band": latest.get("band"),
        },
        "prv_candidates": prv,
    }


class ANTARESBROKER(BrokerAPI):
    """The ANTARES broker (NOIRLab, https://antares.noirlab.edu, ZTF + LSST).

    Interactive access via the public (no-auth) ANTARES JSON:API REST endpoint
    (hit directly with ``requests``, no client dependency): locus lookup + light
    curve, cone search, and science/template/difference thumbnails (PNG). ANTARES
    ingests both surveys into loci; select which one a ``Broker`` serves via
    ``altdata['survey']`` (ZTF mag-space alerts keyed by objectId; LSST flux-space
    diaSources keyed by diaObjectId).
    """

    surveys = ["ZTF", "LSST"]

    form_json_schema_config = {
        "type": "object",
        "properties": {
            "survey": {
                "type": "string",
                "enum": ["ZTF", "LSST"],
                "default": "ZTF",
            },
        },
    }

    @staticmethod
    def validate_config(altdata):
        # ANTARES' REST API is public; no credentials required.
        return

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        survey = _survey(broker)
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return [ANTARESBROKER.get_alert(broker, object_id, session, **kwargs)]
        ra, dec = kwargs.get("ra"), kwargs.get("dec")
        if ra is not None and dec is not None:
            loci = _search_loci(
                broker, _cone_query(ra, dec, kwargs.get("radius", 5)), DEFAULT_LIMIT
            )
            return [_normalize(locus, survey) for locus in loci]
        raise ValueError("Provide objectId, or ra+dec.")

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        survey = _survey(broker)
        locus = _locus(broker, alert_id, survey)
        if locus is None:
            raise ValueError(f"No ANTARES locus for {alert_id}")
        return _normalize(locus, survey)

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        survey = _survey(broker)
        loci = _search_loci(broker, _cone_query(ra, dec, radius), DEFAULT_LIMIT)
        return [_normalize(locus, survey) for locus in loci]

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        """Fetch the latest alert's science/template/difference thumbnails (PNG)
        and return them as data: URLs (the frontend uses them directly).
        ``alert_id`` is the objectId."""
        locus = _locus(broker, alert_id, _survey(broker))
        if locus is None:
            return {}
        alerts = sorted(getattr(locus, "alerts", None) or [], key=lambda a: a.mjd or 0)
        if not alerts:
            return {}
        result = _get(broker, f"alerts/{alerts[-1].alert_id}/thumbnails")
        thumbs = {}
        for item in (result or {}).get("data", []):
            attrs = item.get("attributes", {}) or {}
            if attrs.get("thumbnail_type") and attrs.get("src"):
                thumbs[attrs["thumbnail_type"]] = attrs["src"]
        cutouts = {}
        for kind, field in (
            ("science", "cutoutScience"),
            ("template", "cutoutTemplate"),
            ("difference", "cutoutDifference"),
        ):
            src = thumbs.get(kind)
            if not src:
                continue
            blob = requests.get(src, timeout=DEFAULT_TIMEOUT)
            if blob.ok:
                encoded = base64.b64encode(blob.content).decode("utf-8")
                cutouts[field] = f"data:image/png;base64,{encoded}"
        return cutouts

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Poll ANTARES (its public REST search) for loci matching each configured
        Elasticsearch query (e.g. by tag) and register them as Candidates under
        ``filter_ids``. Config in ``broker.altdata``: ``queries`` (list of ES
        query dicts), ``filter_ids``, ``poll_interval``, ``limit``."""
        import asyncio

        import sqlalchemy as sa

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        survey = altdata.get("survey", "ZTF")
        filter_ids = altdata.get("filter_ids") or []
        # Default: most-recently-updated loci (users add a tag/term filter).
        queries = altdata.get("queries") or [{"query": {"match_all": {}}}]
        poll_interval = float(altdata.get("poll_interval", 3600))
        limit = int(altdata.get("limit", 50))

        def _stopped():
            return stop is not None and stop.is_set()

        count = 0
        while not _stopped():
            for query in queries:
                try:
                    loci = await asyncio.to_thread(_search_loci, broker, query, limit)
                except Exception as e:
                    log(f"ANTARES search failed: {e}")
                    continue
                for locus in loci:
                    if _stopped():
                        break
                    try:
                        data = _normalize(locus, survey.upper())
                        if not data.get("objectId"):
                            continue
                        async with async_plain_session_factory() as session:
                            user = await session.scalar(
                                sa.select(User).where(User.id == 1)
                            )
                            await save_object_as_candidate(
                                data, survey, session, user, filter_ids
                            )
                    except Exception as e:
                        log(f"Error ingesting ANTARES locus: {e}")
                    count += 1
                    if max_messages is not None and count >= max_messages:
                        log(
                            f"ANTARES ingestion (broker {broker.id}): "
                            f"ingested {count} loci"
                        )
                        return count
            if max_messages is not None:
                break  # bounded mode: a single pass
            slept = 0.0
            while slept < poll_interval and not _stopped():
                await asyncio.sleep(min(5.0, poll_interval - slept))
                slept += 5.0
        log(f"ANTARES ingestion (broker {broker.id}): ingested {count} loci")
        return count
