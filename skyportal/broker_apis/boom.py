from datetime import UTC, datetime, timedelta, timezone

import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/boom")

DEFAULT_SURVEY = "ZTF"
DEFAULT_TIMEOUT = 30  # seconds
RADIUS_UNIT_MAP = {"deg": "Degrees", "arcmin": "Arcminutes", "arcsec": "Arcseconds"}
NO_CUTOUT_PROJECTION = {"cutoutScience": 0, "cutoutTemplate": 0, "cutoutDifference": 0}

# token cache keyed by (base_url, username): (token, expiry). Providers are
# stateless, so the short-lived bearer token is cached at module scope.
_TOKENS: dict = {}


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

                survey = record.get("survey", DEFAULT_SURVEY)
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
