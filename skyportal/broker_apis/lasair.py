import base64

import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/lasair")

DEFAULT_ENDPOINT = "https://api.lasair.lsst.ac.uk/api"
DEFAULT_TIMEOUT = 30  # seconds
# Lasair cutout image kind -> skyportal cutout field.
_CUTOUT_KINDS = {
    "Science": "cutoutScience",
    "Template": "cutoutTemplate",
    "Difference": "cutoutDifference",
}
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


def _band(cand):
    return _FID_TO_BAND.get(cand.get("fid")) or (cand.get("filter") or None)


def _normalize_object(obj, object_id):
    """Reshape a Lasair object into the standard alert shape the rest of the
    stack consumes: ``{objectId, candidate, prv_candidates}``."""
    object_data = obj.get("objectData") or {}
    candidates = obj.get("candidates") or []
    detections = [c for c in candidates if c.get("magpsf") is not None]
    latest = detections[0] if detections else (candidates[0] if candidates else {})
    prv_candidates = [
        {
            "jd": c.get("jd"),
            "magpsf": c.get("magpsf"),
            "sigmapsf": c.get("sigmapsf"),
            "band": _band(c),
            "ra": c.get("ra"),
            "dec": c.get("dec"),
        }
        for c in detections
    ]
    return {
        "objectId": obj.get("objectId") or object_id,
        "candidate": {
            "candid": latest.get("candid"),
            "ra": latest.get("ra") or object_data.get("ramean"),
            "dec": latest.get("dec") or object_data.get("decmean"),
            "magpsf": latest.get("magpsf"),
            "jd": latest.get("jd"),
            "band": _band(latest),
        },
        "prv_candidates": prv_candidates,
    }


def _client(broker):
    """Build a Lasair client from ``broker.altdata`` (lazy import so the
    ``lasair`` package is only required by deployments that use Lasair)."""
    import lasair

    altdata = broker.altdata or {}
    token = altdata.get("token")
    if not token:
        raise ValueError("Broker altdata is missing 'token'.")
    endpoint = altdata.get("endpoint", DEFAULT_ENDPOINT)
    return lasair.lasair_client(token=token, endpoint=endpoint)


class LASAIRBROKER(BrokerAPI):
    """The Lasair broker (https://lasair.lsst.ac.uk).

    Interactive access via the ``lasair`` REST client. Configure a ``Broker``
    with ``altdata = {"token": "...", "endpoint": "..."}`` (endpoint defaults to
    the LSST instance).
    """

    surveys = ["ZTF", "LSST"]
    filter_kind = "query"

    form_json_schema_config = {
        "type": "object",
        "required": ["token"],
        "properties": {
            "token": {"type": "string", "title": "Lasair API token"},
            "endpoint": {
                "type": "string",
                "title": "API endpoint",
                "default": DEFAULT_ENDPOINT,
            },
        },
    }

    ui_json_schema = {"token": {"ui:widget": "password"}}

    @staticmethod
    def validate_config(altdata):
        if not (altdata or {}).get("token"):
            raise ValueError("Broker altdata must include 'token'.")

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        client = _client(broker)
        # object id -> single object; ra/dec -> cone search; otherwise a raw
        # SQL-style query (selected/tables/conditions).
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return client.object(object_id)
        if kwargs.get("ra") is not None and kwargs.get("dec") is not None:
            return client.cone(
                float(kwargs["ra"]),
                float(kwargs["dec"]),
                radius=float(kwargs.get("radius", 5)),
                requestType=kwargs.get("requestType", "all"),
            )
        if kwargs.get("selected") and kwargs.get("tables"):
            return client.query(
                kwargs["selected"],
                kwargs["tables"],
                kwargs.get("conditions", ""),
                limit=int(kwargs.get("limit", 1000)),
            )
        raise ValueError(
            "Provide objectId, or ra+dec (cone), or selected+tables (query)."
        )

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        # Normalize into the standard {objectId, candidate, prv_candidates} shape.
        return _normalize_object(_client(broker).object(alert_id), alert_id)

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        return _client(broker).cone(
            float(ra),
            float(dec),
            radius=float(radius),
            requestType=kwargs.get("requestType", "all"),
        )

    @staticmethod
    def test_filter(broker, session, **kwargs):
        # Run a Lasair SQL query and return the matching rows (renderable as
        # alerts). Callers supply `selected`, `tables`, `conditions`, `limit`.
        selected = (
            kwargs.get("selected")
            or "objects.objectId, objects.ramean, objects.decmean"
        )
        tables = kwargs.get("tables") or "objects"
        conditions = kwargs.get("conditions") or ""
        limit = int(kwargs.get("limit", 50))
        return _client(broker).query(selected, tables, conditions, limit=limit)

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        # Lasair keys cutouts by object (not candid): the object record carries
        # FITS image URLs under lasairData.imageUrls; download and base64-encode
        # them into the standard cutout fields.
        obj = _client(broker).object(alert_id)
        # The image-URL location differs by Lasair instance:
        #  - ZTF: the latest candidate carries ``image_urls``
        #  - LSST: ``lasairData.imageUrls`` (a list of per-epoch url dicts)
        image_urls = {}
        candidates = obj.get("candidates") or []
        if (
            candidates
            and isinstance(candidates[0], dict)
            and candidates[0].get("image_urls")
        ):
            image_urls = candidates[0]["image_urls"]
        elif obj.get("image_urls"):
            image_urls = obj["image_urls"]
        else:
            urls = (obj.get("lasairData", {}) or {}).get("imageUrls")
            if isinstance(urls, list) and urls:
                image_urls = urls[0]
            elif isinstance(urls, dict):
                image_urls = urls
        cutouts = {}
        for kind, field in _CUTOUT_KINDS.items():
            url = image_urls.get(kind)
            if not url:
                continue
            try:
                response = requests.get(url, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                cutouts[field] = base64.b64encode(response.content).decode("utf-8")
            except Exception as e:
                log(f"Failed to fetch {kind} cutout for {alert_id}: {e}")
        return cutouts

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Poll Lasair: run each configured SQL query, and for every returned
        object reuse this provider's own ``get_alert``/``get_cutouts`` to build the
        standard alert, then register a Candidate under ``filter_ids``. Config in
        ``broker.altdata``: ``queries`` (list of {name, fields, tables, conditions,
        [filter_ids]}), ``filter_ids``, ``survey``, ``poll_interval``, ``limit``.
        """
        import asyncio

        import sqlalchemy as sa

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        survey = altdata.get("survey", "LSST")
        default_filter_ids = altdata.get("filter_ids") or []
        queries = altdata.get("queries") or []
        poll_interval = float(altdata.get("poll_interval", 86400))
        limit = int(altdata.get("limit", 1000))
        client = _client(broker)

        def _stopped():
            return stop is not None and stop.is_set()

        count = 0
        while not _stopped():
            for query in queries:
                selected = (
                    query.get("fields")
                    or "objects.objectId, objects.ramean, objects.decmean"
                )
                tables = query.get("tables", "objects")
                conditions = query.get("conditions", "")
                filter_ids = query.get("filter_ids") or default_filter_ids
                try:
                    rows = await asyncio.to_thread(
                        client.query, selected, tables, conditions, limit
                    )
                except Exception as e:
                    log(f"Lasair query '{query.get('name')}' failed: {e}")
                    continue
                for row in rows or []:
                    if _stopped():
                        break
                    oid = (
                        row.get("diaObjectId")
                        or row.get("objectId")
                        or row.get("object")
                    )
                    if oid is None:
                        continue
                    oid = str(oid)
                    try:
                        obj = await asyncio.to_thread(client.object, oid)
                        data = _normalize_object(obj, oid)
                        try:
                            cutouts = await asyncio.to_thread(
                                LASAIRBROKER.get_cutouts, broker, oid, None
                            )
                        except Exception:
                            cutouts = None
                        async with async_plain_session_factory() as session:
                            user = await session.scalar(
                                sa.select(User).where(User.id == 1)
                            )
                            await save_object_as_candidate(
                                data,
                                survey,
                                session,
                                user,
                                filter_ids,
                                passing_alert_id=data.get("candidate", {}).get(
                                    "candid"
                                ),
                                cutouts=cutouts or None,
                            )
                    except Exception as e:
                        log(f"Error ingesting Lasair object {oid}: {e}")
                    count += 1
                    if max_messages is not None and count >= max_messages:
                        log(
                            f"Lasair ingestion (broker {broker.id}): "
                            f"ingested {count} objects"
                        )
                        return count
            if max_messages is not None:
                break  # bounded mode: a single pass
            # Sleep until the next poll, waking periodically to honor ``stop``.
            slept = 0.0
            while slept < poll_interval and not _stopped():
                await asyncio.sleep(min(5.0, poll_interval - slept))
                slept += 5.0
        log(f"Lasair ingestion (broker {broker.id}): ingested {count} objects")
        return count
