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


def _survey(broker, kwargs=None):
    """Resolve the Lasair instance's survey: explicit kwarg -> altdata.survey ->
    detected from the endpoint (only the ZTF instance's host contains 'ztf')."""
    altdata = broker.altdata or {}
    survey = (kwargs or {}).get("survey") or altdata.get("survey")
    if not survey:
        endpoint = (altdata.get("endpoint") or DEFAULT_ENDPOINT).lower()
        survey = "ZTF" if "ztf" in endpoint else "LSST"
    return survey.upper()


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


# Mongo-style operators (what the shared builder emits) -> SQL comparison ops.
_SQL_OPS = {"$eq": "=", "$ne": "!=", "$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}


def _sql_value(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _compile_tree_to_sql(node):
    """Compile the builder's neutral condition tree (blocks of AND/OR + field/
    operator/value conditions, the same shape BOOM compiles to a Mongo pipeline)
    into a Lasair SQL WHERE clause."""
    if not isinstance(node, dict):
        return ""
    if node.get("category") == "block" or "children" in node:
        joiner = (node.get("operator") or "and").upper()
        parts = [_compile_tree_to_sql(c) for c in (node.get("children") or [])]
        parts = [p for p in parts if p]
        return "(" + f" {joiner} ".join(parts) + ")" if parts else ""
    field = node.get("field")
    field = field.get("name") if isinstance(field, dict) else field
    if not field:
        return ""
    operator, value = node.get("operator"), node.get("value")
    if operator == "$in" and isinstance(value, list):
        return f"{field} IN (" + ", ".join(_sql_value(v) for v in value) + ")"
    if operator == "$regex":
        return f"{field} LIKE {_sql_value('%' + str(value) + '%')}"
    sqlop = _SQL_OPS.get(operator)
    return f"{field} {sqlop} {_sql_value(value)}" if sqlop else ""


def _lasair_schema(survey):
    """A minimal Avro-style schema of queryable Lasair ``objects`` columns for the
    builder's field dropdowns (so users pick valid columns instead of typing SQL).
    Column names differ by instance (ZTF vs LSST)."""
    if survey == "LSST":
        fields = [
            {"name": "objects.diaObjectId", "type": "string"},
            {"name": "objects.ra", "type": "double"},
            {"name": "objects.decl", "type": "double"},
            {"name": "objects.nDiaSources", "type": "int"},
            {"name": "objects.gPSFluxMean", "type": "double"},
            {"name": "objects.rPSFluxMean", "type": "double"},
        ]
    else:
        fields = [
            {"name": "objects.objectId", "type": "string"},
            {"name": "objects.ramean", "type": "double"},
            {"name": "objects.decmean", "type": "double"},
            {"name": "objects.ndethist", "type": "int"},
            {"name": "objects.gmag", "type": "double"},
            {"name": "objects.rmag", "type": "double"},
        ]
    return {"type": "record", "name": "objects", "fields": fields}


def _token(broker):
    token = (broker.altdata or {}).get("token")
    if not token:
        raise ValueError("Broker altdata is missing 'token'.")
    return token


def _endpoint(broker):
    return (broker.altdata or {}).get("endpoint", DEFAULT_ENDPOINT)


def _request(broker, method, data):
    """Call a Lasair REST method: ``POST {endpoint}/{method}/`` with form data and
    a ``Authorization: Token`` header (what the ``lasair`` client does, so no
    dependency). Returns the parsed JSON."""
    url = _endpoint(broker).rstrip("/") + "/" + method + "/"
    headers = {"Authorization": f"Token {_token(broker)}"}
    response = requests.post(url, data=data, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _object(broker, object_id):
    return _request(
        broker,
        "object",
        {"objectId": object_id, "lite": True, "lasair_added": True},
    )


def _cone(broker, ra, dec, radius=5, request_type="all"):
    return _request(
        broker,
        "cone",
        {"ra": ra, "dec": dec, "radius": radius, "requestType": request_type},
    )


def _query(broker, selected, tables, conditions, limit=1000):
    return _request(
        broker,
        "query",
        {
            "selected": selected,
            "tables": tables,
            "conditions": conditions,
            "limit": limit,
        },
    )


class LASAIRBROKER(BrokerAPI):
    """The Lasair broker (https://lasair.lsst.ac.uk).

    Interactive access via Lasair's REST API (called directly with ``requests``,
    no client dependency). Configure a ``Broker`` with ``altdata = {"token":
    "...", "endpoint": "..."}`` (endpoint defaults to the LSST instance).
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
        # object id -> single object; ra/dec -> cone search; otherwise a raw
        # SQL-style query (selected/tables/conditions).
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return _object(broker, object_id)
        if kwargs.get("ra") is not None and kwargs.get("dec") is not None:
            return _cone(
                broker,
                float(kwargs["ra"]),
                float(kwargs["dec"]),
                radius=float(kwargs.get("radius", 5)),
                request_type=kwargs.get("requestType", "all"),
            )
        if kwargs.get("selected") and kwargs.get("tables"):
            return _query(
                broker,
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
        return _normalize_object(_object(broker, alert_id), alert_id)

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        return _cone(
            broker,
            float(ra),
            float(dec),
            radius=float(radius),
            request_type=kwargs.get("requestType", "all"),
        )

    @staticmethod
    def filter_modules(broker, session, **kwargs):
        """Field vocabulary for the shared filter builder. ``elements=schema``
        (default) returns the queryable Lasair columns as an Avro-style schema so
        the builder offers valid fields; other elements are broker-scoped custom
        modules stored in altdata (same as BOOM)."""
        elements = kwargs.get("elements", "schema")
        if elements == "schema":
            return {"schema": _lasair_schema(_survey(broker, kwargs))}
        modules = (broker.altdata or {}).get("filter_modules") or {}
        return {elements: modules.get(elements, [])}

    @staticmethod
    def test_filter(broker, session, **kwargs):
        # Run a Lasair SQL query and return the matching rows (renderable as
        # alerts). Accepts either raw ``conditions`` (SQL) or a neutral condition
        # ``tree`` from the shared builder, compiled here to SQL. Object-id/coord
        # columns differ by instance (ZTF vs LSST).
        survey = _survey(broker, kwargs)
        default_selected = (
            "objects.diaObjectId, objects.ra, objects.decl"
            if survey == "LSST"
            else "objects.objectId, objects.ramean, objects.decmean"
        )
        selected = kwargs.get("selected") or default_selected
        tables = kwargs.get("tables") or "objects"
        tree = kwargs.get("tree") or kwargs.get("filters")
        if tree is not None:
            # The builder holds a list of top-level blocks; AND them together.
            if isinstance(tree, list):
                tree = {"operator": "and", "children": tree}
            conditions = _compile_tree_to_sql(tree)
        else:
            conditions = kwargs.get("conditions") or ""
        limit = int(kwargs.get("limit", 50))
        return _query(broker, selected, tables, conditions, limit=limit)

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        # Lasair keys cutouts by object (not candid): the object record carries
        # FITS image URLs under lasairData.imageUrls; download and base64-encode
        # them into the standard cutout fields.
        obj = _object(broker, alert_id)
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
        survey = _survey(broker)
        default_filter_ids = altdata.get("filter_ids") or []
        queries = altdata.get("queries") or []
        poll_interval = float(altdata.get("poll_interval", 86400))
        limit = int(altdata.get("limit", 1000))

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
                        _query, broker, selected, tables, conditions, limit
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
                        obj = await asyncio.to_thread(_object, broker, oid)
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
