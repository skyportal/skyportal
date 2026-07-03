import base64

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/antares")

# ANTARES ZTF alerts use fid (1=g, 2=R); the client exposes ant_passband too.
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}
DEFAULT_LIMIT = 20


def _locus(alert_id):
    """Fetch an ANTARES locus by ZTF objectId or ANTARES locus id (lazy import so
    the ``antares-client`` package is only needed by deployments that use it)."""
    from antares_client.search import get_by_id, get_by_ztf_object_id

    locus = None
    if str(alert_id).startswith("ZTF"):
        locus = get_by_ztf_object_id(alert_id)
    if locus is None:
        locus = get_by_id(alert_id)
    return locus


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
    """The ANTARES broker (NOIRLab, https://antares.noirlab.edu, ZTF alerts).

    Interactive access via the public (no-auth) ``antares-client`` REST API:
    locus lookup + light curve, cone search, and science/template/difference
    thumbnails (PNG). Configure a ``Broker`` with an empty ``altdata``.
    """

    surveys = ["ZTF"]

    form_json_schema_config = {
        "type": "object",
        "properties": {
            "survey": {"type": "string", "enum": ["ZTF"], "default": "ZTF"},
        },
    }

    @staticmethod
    def validate_config(altdata):
        # ANTARES' REST API is public; no credentials required.
        return

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return [ANTARESBROKER.get_alert(broker, object_id, session, **kwargs)]
        ra, dec = kwargs.get("ra"), kwargs.get("dec")
        if ra is not None and dec is not None:
            from antares_client.search import cone_search
            from astropy.coordinates import Angle, SkyCoord

            center = SkyCoord(float(ra), float(dec), unit="deg")
            radius = Angle(f"{kwargs.get('radius', 5)}s")  # arcsec
            out = []
            for locus in cone_search(center, radius):
                out.append(_normalize_locus(locus))
                if len(out) >= DEFAULT_LIMIT:
                    break
            return out
        raise ValueError("Provide objectId, or ra+dec.")

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        locus = _locus(alert_id)
        if locus is None:
            raise ValueError(f"No ANTARES locus for {alert_id}")
        return _normalize_locus(locus)

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        from antares_client.search import cone_search
        from astropy.coordinates import Angle, SkyCoord

        center = SkyCoord(float(ra), float(dec), unit="deg")
        out = []
        for locus in cone_search(center, Angle(f"{radius}s")):
            out.append(_normalize_locus(locus))
            if len(out) >= DEFAULT_LIMIT:
                break
        return out

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        """Fetch the latest alert's science/template/difference thumbnails (PNG)
        and return them as data: URLs (the frontend uses them directly).
        ``alert_id`` is the objectId."""
        from antares_client.search import get_thumbnails

        locus = _locus(alert_id)
        if locus is None:
            return {}
        alerts = sorted(getattr(locus, "alerts", None) or [], key=lambda a: a.mjd or 0)
        if not alerts:
            return {}
        thumbs = get_thumbnails(alerts[-1].alert_id)
        cutouts = {}
        for kind, field in (
            ("science", "cutoutScience"),
            ("template", "cutoutTemplate"),
            ("difference", "cutoutDifference"),
        ):
            entry = thumbs.get(kind) if isinstance(thumbs, dict) else None
            blob = entry.get("blob") if isinstance(entry, dict) else None
            if blob:
                encoded = base64.b64encode(blob).decode("utf-8")
                cutouts[field] = f"data:image/png;base64,{encoded}"
        return cutouts

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Poll ANTARES (its public REST search) for loci matching each configured
        Elasticsearch query (e.g. by tag) and register them as Candidates under
        ``filter_ids``. Config in ``broker.altdata``: ``queries`` (list of ES
        query dicts), ``filter_ids``, ``poll_interval``, ``limit``."""
        import asyncio
        from itertools import islice

        import sqlalchemy as sa
        from antares_client.search import search

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
                    loci = await asyncio.to_thread(
                        lambda q=query: list(islice(search(q), limit))
                    )
                except Exception as e:
                    log(f"ANTARES search failed: {e}")
                    continue
                for locus in loci:
                    if _stopped():
                        break
                    try:
                        data = _normalize_locus(locus)
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
