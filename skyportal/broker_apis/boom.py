from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone

import requests
from pymongo import MongoClient

from baselayer.app.env import load_env
from baselayer.log import make_log

from .interface import BrokerAPI, normalize_module_streams

log = make_log("broker/boom")

_, cfg = load_env()

DEFAULT_SURVEY = "ZTF"
DEFAULT_TIMEOUT = 30  # seconds
RADIUS_UNIT_MAP = {"deg": "Degrees", "arcmin": "Arcminutes", "arcsec": "Arcseconds"}
NO_CUTOUT_PROJECTION = {"cutoutScience": 0, "cutoutTemplate": 0, "cutoutDifference": 0}

# token cache keyed by (base_url, username): (token, expiry). Providers are
# stateless, so the short-lived bearer token is cached at module scope.
_TOKENS: dict = {}

# One MongoClient per store URI (the client pools connections internally).
_MONGO_CLIENTS: dict = {}


def _base_url(altdata):
    protocol = altdata.get("protocol", "https")
    host = altdata.get("host")
    if not host:
        raise ValueError("Broker altdata is missing 'host'.")
    port = altdata.get("port")
    suffix = f":{port}" if port and int(port) not in (80, 443) else ""
    return f"{protocol}://{host}{suffix}"


def _get_token(altdata, force=False):
    base_url = _base_url(altdata)
    username = altdata.get("username")
    password = altdata.get("password")
    if not username or not password:
        raise ValueError("Broker altdata must include 'username' and 'password'.")
    key = (base_url, username)
    cached = _TOKENS.get(key)
    if not force and cached and datetime.now(UTC) < cached[1]:
        return cached[0]
    response = requests.post(
        f"{base_url}/auth",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": username, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    token = data["access_token"]
    expiry = datetime.now(UTC) + timedelta(seconds=data.get("expires_in", 3600))
    _TOKENS[key] = (token, expiry)
    return token


def _request(broker, method, path, *, params=None, json=None):
    """Authenticated BOOM request; refreshes the token once on a 401."""
    altdata = broker.altdata or {}
    base_url = _base_url(altdata)
    url = f"{base_url}/{path.lstrip('/')}"
    for attempt in range(2):
        token = _get_token(altdata, force=(attempt == 1))
        response = requests.request(
            method,
            url,
            params=params,
            json=json,
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code != 401:
            break
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def _survey(broker, kwargs):
    return kwargs.get("survey") or (broker.altdata or {}).get("survey", DEFAULT_SURVEY)


def _record_survey(record):
    """The survey of a BOOM Kafka record, uppercased: BOOM emits title-case names
    ("Ztf") but skyportal keys instruments/zeropoints/streams on the upper form,
    so a verbatim name drops every alert (`Instrument 'Ztf' not found`)."""
    return (record.get("survey") or DEFAULT_SURVEY).upper()


def _modules_db(broker):
    """The MongoDB database holding BOOM's user-created filter modules.

    Resolved from the broker's altdata, falling back to the global
    ``boom.filter_modules`` config. Returns ``None`` when unconfigured so reads
    degrade to empty lists rather than raising.
    """
    altdata = broker.altdata or {}
    conf = cfg.get("boom.filter_modules") or {}
    uri = altdata.get("filter_modules_mongodb_uri") or conf.get("mongodb_uri")
    database = altdata.get("filter_modules_database") or conf.get("database")
    if not uri or not database:
        log(
            f"BOOM broker {broker.id}: no filter-module store configured "
            "(boom.filter_modules.mongodb_uri/database)."
        )
        return None
    client = _MONGO_CLIENTS.get(uri)
    if client is None:
        client = _MONGO_CLIENTS[uri] = MongoClient(uri)
    return client[database]


# BOOM's Kafka alert sentinel for "no value" in flux fields.
_BOOM_SENTINEL = -99999.0


def _normalize_boom_alert(record):
    """Convert a BOOM Kafka Avro alert (native ``photometry[]`` with flux in nJy)
    into the standard alert shape (``candidate`` + ``prv_candidates`` with
    ``psfFlux``/``psfFluxErr``) consumed by the shared save transform."""
    prv = []
    for p in record.get("photometry") or []:
        flux_err = p.get("flux_err")
        if flux_err is None or flux_err == _BOOM_SENTINEL:
            continue
        flux = p.get("flux")
        if flux == _BOOM_SENTINEL:
            flux = None
        prv.append(
            {
                "jd": p.get("jd"),
                "band": p.get("band"),
                "psfFlux": flux,  # nJy; the shared save scales by 1e-9 to Jy
                "psfFluxErr": flux_err,
                "ra": p.get("ra"),
                "dec": p.get("dec"),
                "programid": p.get("programid", 1),
            }
        )
    return {
        "objectId": record.get("objectId"),
        "candid": record.get("candid"),
        "candidate": {
            "ra": record.get("ra"),
            "dec": record.get("dec"),
            "drb": record.get("drb"),
        },
        "prv_candidates": prv,
    }


# Collections that belong to surveys/alerts, not reference catalogs.
_SURVEY_CATALOG_PREFIXES = ("ZTF_", "LSST_", "PTF_", "PGIR_", "WNTR_")
_CATALOGS_TTL = timedelta(hours=1)
# base_url -> (catalog_names, expiry); the reference-catalog list is stable, so
# cache it to avoid hitting /catalogs on every cross-match.
_CATALOGS_CACHE: dict = {}


def _reference_catalogs(broker):
    """BOOM's non-survey (reference) catalog names, cached per host with a TTL."""
    base_url = _base_url(broker.altdata or {})
    cached = _CATALOGS_CACHE.get(base_url)
    if cached and datetime.now(UTC) < cached[1]:
        return cached[0]
    catalogs = _request(broker, "GET", "catalogs") or []
    names = [
        str(c["name"])
        for c in catalogs
        if isinstance(c, dict)
        and c.get("name")
        and not str(c["name"]).startswith(_SURVEY_CATALOG_PREFIXES)
    ]
    _CATALOGS_CACHE[base_url] = (names, datetime.now(UTC) + _CATALOGS_TTL)
    return names


def _cone_search_catalog(broker, catalog, ra, dec, radius, unit):
    """Cone-search one BOOM catalog; returns ``(catalog, [normalized sources])``."""
    try:
        data = _request(
            broker,
            "POST",
            "queries/cone_search",
            json={
                "catalog_name": catalog,
                "object_coordinates": {"query": [ra, dec]},
                "radius": radius,
                "unit": unit,
                "max_time_ms": 5000,
            },
        )
    except Exception as e:
        log(f"cone_search against {catalog} failed: {e}")
        return catalog, []
    results = (data or {}).get("query", []) if isinstance(data, dict) else []
    for source in results:
        source["_id"] = str(source.get("_id", ""))
        coords = (
            source.get("coordinates", {})
            .get("radec_geojson", {})
            .get("coordinates", [])
        )
        if len(coords) == 2:
            # BOOM stores GeoJSON longitude in [-180, 180]; shift back to RA.
            source["ra"] = coords[0] + 180
            source["dec"] = coords[1]
    return catalog, results


class BOOMBROKER(BrokerAPI):
    """The BOOM broker (kaboom.caltech.edu, ZTF/LSST alerts).

    Talks to BOOM's REST API: username/password -> bearer token (``/auth``),
    Mongo-style ``/queries/find`` and ``/queries/cone_search``,
    ``/queries/pipeline`` for the full object, and ``/surveys/{survey}/cutouts``.
    Configure a ``Broker`` with ``altdata = {"protocol", "host", "port",
    "username", "password", "survey"}``.
    """

    surveys = ["ZTF", "LSST"]
    filter_kind = "pipeline"
    # cone_search returns BOOM's reference catalogs (Gaia/PS1/AllWISE, ...).
    cross_match_catalogs = True

    form_json_schema_config = {
        "type": "object",
        "required": ["host", "username", "password"],
        "properties": {
            "protocol": {"type": "string", "default": "https"},
            "host": {
                "type": "string",
                "title": "API host (e.g. api.kaboom.caltech.edu)",
            },
            "port": {"type": "integer", "default": 443},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "survey": {
                "type": "string",
                "enum": ["ZTF", "LSST"],
                "default": DEFAULT_SURVEY,
            },
        },
    }

    ui_json_schema = {"password": {"ui:widget": "password"}}

    @staticmethod
    def validate_config(altdata):
        altdata = altdata or {}
        for key in ("host", "username", "password"):
            if not altdata.get(key):
                raise ValueError(f"Broker altdata must include '{key}'.")

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        survey = _survey(broker, kwargs)
        catalog = f"{survey}_alerts"
        object_id = kwargs.get("objectId")
        ra, dec, radius = kwargs.get("ra"), kwargs.get("dec"), kwargs.get("radius")

        if object_id:
            return _request(
                broker,
                "POST",
                "queries/find",
                json={
                    "catalog_name": catalog,
                    "filter": {"objectId": object_id},
                    "projection": NO_CUTOUT_PROJECTION,
                    "max_time_ms": 10000,
                },
            )
        if ra is not None and dec is not None and radius is not None:
            unit = RADIUS_UNIT_MAP.get(
                kwargs.get("radius_units", "arcsec"), "Arcseconds"
            )
            result = _request(
                broker,
                "POST",
                "queries/cone_search",
                json={
                    "catalog_name": catalog,
                    "object_coordinates": {"query": [float(ra), float(dec)]},
                    "radius": float(radius),
                    "unit": unit,
                    "max_time_ms": 10000,
                },
            )
            return result.get("query", []) if isinstance(result, dict) else result
        raise ValueError("Provide objectId, or ra+dec+radius.")

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        # Full object: brightest alert joined with its aux history.
        survey = _survey(broker, kwargs)
        catalog = f"{survey}_alerts"
        pipeline = [
            {"$match": {"objectId": alert_id}},
            {"$sort": {"candidate.magpsf": 1}},
            {"$group": {"_id": "$objectId", "data": {"$first": "$$ROOT"}}},
            {"$replaceRoot": {"newRoot": "$data"}},
            {
                "$lookup": {
                    "from": f"{catalog}_aux",
                    "localField": "objectId",
                    "foreignField": "_id",
                    "as": "aux",
                }
            },
            {"$unwind": {"path": "$aux", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "_id": 1,
                    "objectId": 1,
                    "candid": 1,
                    "candidate": 1,
                    "prv_candidates": "$aux.prv_candidates",
                    "prv_nondetections": "$aux.prv_nondetections",
                    "fp_hists": "$aux.fp_hists",
                }
            },
        ]
        data = _request(
            broker,
            "POST",
            "queries/pipeline",
            json={"catalog_name": catalog, "pipeline": pipeline, "max_time_ms": 30000},
        )
        return data[0] if isinstance(data, list) and data else data

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        survey = _survey(broker, kwargs)
        return _request(
            broker,
            "GET",
            f"surveys/{survey}/cutouts",
            params={"candid": alert_id},
        )

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        """Cross-match a position against BOOM's reference catalogs (Gaia, PS1,
        AllWISE, ...). Returns ``{catalog_name: [sources]}`` for catalogs with a
        hit; each catalog is searched concurrently."""
        unit = RADIUS_UNIT_MAP.get(kwargs.get("radius_units", "arcsec"))
        if unit is None:
            raise ValueError("radius_units must be one of 'deg', 'arcmin', 'arcsec'.")
        catalogs = _reference_catalogs(broker)
        results = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            for catalog, sources in pool.map(
                lambda c: _cone_search_catalog(broker, c, ra, dec, radius, unit),
                catalogs,
            ):
                if sources:
                    results[catalog] = sources
        return results

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Consume BOOM's Kafka filter-result streams (Avro) and register each
        alert as a Candidate under the skyportal Filters mapped to the BOOM filter
        ids it passed (``Filter.altdata['boom']['filter_id']``), falling back to
        ``broker.altdata['filter_ids']``. Kafka config in ``broker.altdata['kafka']``.
        """
        import asyncio

        import sqlalchemy as sa
        from confluent_kafka import Consumer, KafkaError

        from baselayer.app.models import async_plain_session_factory

        from ..models import Filter, User
        from ._kafka import kafka_consumer_config, read_avro
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        kafka = altdata.get("kafka") or {}
        default_filter_ids = altdata.get("filter_ids") or []

        consumer = Consumer(
            kafka_consumer_config(kafka, f"skyportal-broker-{broker.id}")
        )
        topics = kafka.get("topics") or ["ZTF_alerts_results", "LSST_alerts_results"]
        consumer.subscribe(topics)
        log(f"BOOM ingestion (broker {broker.id}): subscribed to {topics}")

        # Map BOOM filter ids -> skyportal Filter ids once at startup.
        async with async_plain_session_factory() as session:
            boom_map = {}
            for f in (await session.scalars(sa.select(Filter))).all():
                boom = (f.altdata or {}).get("boom") if f.altdata else None
                if boom and boom.get("filter_id") is not None:
                    boom_map[boom["filter_id"]] = f.id

        count = 0
        try:
            while not (stop is not None and stop.is_set()):
                # poll is blocking; offload so one loop can host several brokers.
                msg = await asyncio.to_thread(consumer.poll, 2.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        log(f"Kafka error: {msg.error()}")
                    continue
                record = read_avro(msg.value())
                if record is None:
                    continue

                survey = _record_survey(record)
                data = _normalize_boom_alert(record)
                # Route to the skyportal Filters mapped to the passing BOOM filters.
                passed = [
                    boom_map[f["filter_id"]]
                    for f in (record.get("filters") or [])
                    if f.get("filter_id") in boom_map
                ]
                filter_ids = passed or default_filter_ids
                cutouts = {
                    k: record[k]
                    for k in ("cutoutScience", "cutoutTemplate", "cutoutDifference")
                    if record.get(k) is not None
                } or None
                try:
                    async with async_plain_session_factory() as session:
                        user = await session.scalar(sa.select(User).where(User.id == 1))
                        await save_object_as_candidate(
                            data,
                            survey,
                            session,
                            user,
                            filter_ids,
                            passing_alert_id=record.get("candid"),
                            cutouts=cutouts,
                        )
                except Exception as e:
                    log(f"Error ingesting alert {record.get('objectId')}: {e}")
                count += 1
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            consumer.close()
        log(f"BOOM ingestion (broker {broker.id}): consumed {count} alerts")
        return count

    # ------------------------------------------------------------------ #
    # Filters (BOOM aggregation-pipeline "filters", versioned server-side).
    # These forward to BOOM's REST API via broker.altdata; the generic
    # /api/brokers/{id}/filters handler owns the skyportal Filter row.
    # ------------------------------------------------------------------ #

    @staticmethod
    def filter_modules(broker, session, **kwargs):
        """Filter-building vocabulary for a survey. ``elements`` selects what to
        fetch: "schema" (default) returns BOOM's alert schema (fields/types) over
        REST; the user-created modules (variables/listVariables/switchCases/
        blocks) come from BOOM's own MongoDB store. With ``name``, returns the
        single matching module (or ``None``) instead of the list."""
        elements = kwargs.get("elements", "schema")
        if elements == "schema":
            survey = _survey(broker, kwargs)
            return {"schema": _request(broker, "GET", f"filters/schemas/{survey}")}
        name = kwargs.get("name")
        db = _modules_db(broker)
        if db is None:
            return {elements: None if name else []}
        # Strip the raw ObjectId: it is not JSON-serializable.
        if name:
            return {elements: db[elements].find_one({"name": name}, {"_id": 0})}
        return {elements: list(db[elements].find({}, {"_id": 0}))}

    @staticmethod
    def write_filter_module(broker, session, name, elements, payload, insert):
        """Upsert a custom filter module into BOOM's MongoDB store."""
        db = _modules_db(broker)
        if db is None:
            raise ValueError("No filter-module store is configured for this broker.")
        payload = normalize_module_streams(payload)
        now = datetime.now(UTC)
        if insert:
            db[elements].update_one(
                {"name": name},
                {
                    "$set": {"name": name, **payload, "updated_at": now},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        elif db[elements].find_one({"name": name}, {"_id": 0}) is None:
            raise ValueError(f"No {elements} named '{name}'.")
        else:
            db[elements].update_one(
                {"name": name}, {"$set": {**payload, "updated_at": now}}
            )

    @staticmethod
    def get_filters(broker, session, **kwargs):
        """Fetch a BOOM filter's versions/active state by BOOM filter id."""
        return _request(broker, "GET", f"filters/{kwargs['boom_filter_id']}")

    @staticmethod
    def create_filter(broker, session, **kwargs):
        """Create a filter on BOOM, or add a version to an existing one (when
        ``boom_filter_id`` is given). Returns BOOM's response data (``id`` +
        ``active_fid`` for a new filter, ``fid`` for a new version)."""
        pipeline = kwargs["pipeline"]
        boom_filter_id = kwargs.get("boom_filter_id")
        if boom_filter_id is None:
            return _request(
                broker,
                "POST",
                "filters",
                json={
                    "name": kwargs["name"],
                    "pipeline": pipeline,
                    "survey": kwargs["survey"],
                    "permissions": kwargs["permissions"],
                },
            )
        return _request(
            broker,
            "POST",
            f"filters/{boom_filter_id}/versions",
            json={"pipeline": pipeline},
        )

    @staticmethod
    def update_filter(broker, session, **kwargs):
        """Activate a version (``active``/``active_fid``) on BOOM. ``skip_validation``
        tells BOOM to skip its inline activation check (skyportal gates instead)."""
        payload = {
            k: kwargs[k]
            for k in ("active", "active_fid", "skip_validation")
            if k in kwargs
        }
        return _request(
            broker, "PATCH", f"filters/{kwargs['boom_filter_id']}", json=payload
        )

    @staticmethod
    def validate_filter(broker, session, **kwargs):
        """Run BOOM's activation validation for a version without changing state;
        returns ``{fid, passed, message?}``."""
        params = {"fid": kwargs["fid"]} if kwargs.get("fid") else None
        return _request(
            broker,
            "POST",
            f"filters/{kwargs['boom_filter_id']}/validate",
            params=params,
        )

    @staticmethod
    def delete_filter(broker, session, **kwargs):
        """Best-effort delete on BOOM; the skyportal Filter row is removed by the
        caller (BOOM cascades its own versions)."""
        boom_filter_id = kwargs.get("boom_filter_id")
        if boom_filter_id is not None:
            try:
                _request(broker, "DELETE", f"filters/{boom_filter_id}")
            except Exception as e:
                log(f"BOOM filter {boom_filter_id} delete failed: {e}")
        return {"status": "ok"}

    @staticmethod
    def test_filter(broker, session, **kwargs):
        """Preview a pipeline against BOOM: a count, or sorted/paginated results
        when ``sort_by`` is given (mirrors BOOM's /filters/test[/count]).

        The builder UI sends ``selectedCollection`` (e.g. "ZTF_alerts") + a
        ``filter_id`` rather than an explicit survey/permissions; derive the
        survey from the collection and the stream permissions from the filter."""
        survey = kwargs.get("survey")
        if survey is None and kwargs.get("selectedCollection"):
            survey = str(kwargs["selectedCollection"]).split("_")[0]
        survey = survey or _survey(broker, kwargs)

        permissions = kwargs.get("permissions")
        if permissions is None and kwargs.get("filter_id") is not None:
            import sqlalchemy as sa
            from sqlalchemy.orm import joinedload

            from ..models import Filter

            f = session.scalar(
                sa.select(Filter)
                .options(joinedload(Filter.stream))
                .where(Filter.id == int(kwargs["filter_id"]))
            )
            if f is not None and f.stream and isinstance(f.stream.altdata, dict):
                permissions = {survey: f.stream.altdata.get("selector")}

        payload = {
            "survey": survey,
            "pipeline": kwargs["pipeline"],
            "permissions": permissions or {},
            "start_jd": kwargs.get("start_jd"),
            "end_jd": kwargs.get("end_jd"),
        }
        if kwargs.get("sort_by"):
            payload.update(
                {
                    "sort_by": kwargs["sort_by"],
                    "sort_order": kwargs.get("sort_order", "Descending"),
                    "limit": kwargs.get("limit", 50),
                }
            )
            res = _request(broker, "POST", "filters/test", json=payload)
            if isinstance(res, dict) and isinstance(res.get("results"), list):
                # stringify Mongo _id so large ids survive JS number precision.
                res["results"] = [
                    {**doc, "_id": str(doc.get("_id"))} for doc in res["results"]
                ]
            return res
        return _request(broker, "POST", "filters/test/count", json=payload)
