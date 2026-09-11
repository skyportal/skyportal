import base64
import time

import requests

from baselayer.log import make_log

from .interface import BrokerAPI, altdata_filter_modules

log = make_log("broker/lasair")

DEFAULT_ENDPOINT = "https://api.lasair.lsst.ac.uk/api"
DEFAULT_TIMEOUT = 30  # seconds
CREDENTIAL_RESCAN_INTERVAL = 60  # seconds
CONSUMER_RETRY_PAUSE = 5  # seconds
# Lasair cutout image kind -> skyportal cutout field.
_CUTOUT_KINDS = {
    "Science": "cutoutScience",
    "Template": "cutoutTemplate",
    "Difference": "cutoutDifference",
}
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


def _band(cand):
    return _FID_TO_BAND.get(cand.get("fid")) or (cand.get("filter") or None)


def _survey_from_altdata(altdata, kwargs=None):
    """Resolve a Lasair instance's survey: explicit kwarg -> altdata.survey ->
    detected from the endpoint (only the ZTF instance's host contains 'ztf')."""
    altdata = altdata or {}
    survey = (kwargs or {}).get("survey") or altdata.get("survey")
    if not survey:
        endpoint = (altdata.get("endpoint") or DEFAULT_ENDPOINT).lower()
        survey = "ZTF" if "ztf" in endpoint else "LSST"
    return survey.upper()


def _survey(broker, kwargs=None):
    return _survey_from_altdata(broker.altdata or {}, kwargs)


def _normalize_object(obj, object_id):
    """Reshape a Lasair object into the standard alert shape the rest of the
    stack consumes: ``{objectId, candidate, prv_candidates, annotations}``."""
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
    # Extract annotations from external annotators (e.g. NEEDLE_LSST).
    # Lasair places them in lasairData.annotations when lasair_added=True.
    lasair_data = obj.get("lasairData") or {}
    raw_annotations = lasair_data.get("annotations") or obj.get("annotations") or []
    annotations = []
    for ann in raw_annotations:
        topic = ann.get("topic")
        if not topic:
            continue
        entry = {"topic": topic}
        for key in ("classification", "explanation", "url"):
            if ann.get(key):
                entry[key] = ann[key]
        classdict = ann.get("classdict") or ann.get("classjson")
        if classdict:
            if isinstance(classdict, str):
                try:
                    import json as _json

                    classdict = _json.loads(classdict)
                except Exception:
                    pass
            entry["classdict"] = classdict
        annotations.append(entry)
    return {
        "objectId": obj.get("objectId") or object_id,
        "candidate": {
            "candid": latest.get("candid"),
            "ra": latest.get("ra")
            or object_data.get("ramean")
            or object_data.get("ra"),
            "dec": latest.get("dec")
            or object_data.get("decmean")
            or object_data.get("decl")
            or object_data.get("dec"),
            "magpsf": latest.get("magpsf"),
            "jd": latest.get("jd"),
            "band": _band(latest),
        },
        "prv_candidates": prv_candidates,
        "annotations": annotations,
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
    """Queryable Lasair columns for the builder's field dropdowns, so users pick
    valid columns instead of typing SQL. Column names differ by instance (ZTF vs
    LSST). Watchmaps and annotators are absent on purpose: neither offers columns
    to choose from, so both are reached by raw SQL in the conditions clause."""
    if survey == "LSST":
        fields = [
            {"name": "objects.diaObjectId", "type": "string"},
            {"name": "objects.ra", "type": "double"},
            {"name": "objects.decl", "type": "double"},
            {"name": "objects.nDiaSources", "type": "int"},
            {"name": "objects.nPosDiaSources", "type": "int"},
            {"name": "objects.firstDiaSourceMjdTai", "type": "double"},
            {"name": "objects.lastDiaSourceMjdTai", "type": "double"},
            {"name": "objects.gPSFluxMean", "type": "double"},
            {"name": "objects.rPSFluxMean", "type": "double"},
            {"name": "objects.g_psfFlux", "type": "double"},
            {"name": "objects.r_psfFlux", "type": "double"},
            {"name": "objects.absMag", "type": "double"},
            {"name": "objects.glat", "type": "double"},
            {"name": "objects.ebv", "type": "double"},
            {"name": "objects.tns_name", "type": "string"},
            # Watchlist matches: the join that drives a watchlist-based filter.
            {"name": "watchlist_hits.diaObjectId", "type": "string"},
            {"name": "watchlist_hits.name", "type": "string"},
            {"name": "watchlist_hits.arcsec", "type": "double"},
            {"name": "watchlist_hits.wl_id", "type": "int"},
            {"name": "watchlist_hits.cone_id", "type": "int"},
            {"name": "sherlock_classifications.diaObjectId", "type": "string"},
            {"name": "sherlock_classifications.classification", "type": "string"},
            {"name": "sherlock_classifications.association_type", "type": "string"},
            {
                "name": "sherlock_classifications.catalogue_object_type",
                "type": "string",
            },
            {"name": "sherlock_classifications.separationArcsec", "type": "double"},
            {
                "name": "sherlock_classifications.physical_separation_kpc",
                "type": "double",
            },
            {"name": "sherlock_classifications.z", "type": "double"},
            {"name": "sherlock_classifications.photoZ", "type": "double"},
            {
                "name": "sherlock_classifications.classificationReliability",
                "type": "int",
            },
            {"name": "crossmatch_tns.tns_name", "type": "string"},
            {"name": "crossmatch_tns.tns_prefix", "type": "string"},
            {"name": "crossmatch_tns.type", "type": "string"},
            {"name": "crossmatch_tns.z", "type": "double"},
            {"name": "crossmatch_tns.disc_mag", "type": "double"},
            {"name": "crossmatch_tns.host_name", "type": "string"},
        ]
    else:
        fields = [
            {"name": "objects.objectId", "type": "string"},
            {"name": "objects.ramean", "type": "double"},
            {"name": "objects.decmean", "type": "double"},
            {"name": "objects.ndethist", "type": "int"},
            {"name": "objects.ncand", "type": "int"},
            {"name": "objects.jdmax", "type": "double"},
            {"name": "objects.gmag", "type": "double"},
            {"name": "objects.rmag", "type": "double"},
            {"name": "objects.sgscore1", "type": "double"},
            {"name": "objects.sgmag1", "type": "double"},
            {"name": "objects.glatmean", "type": "double"},
            # Watchlist matches: the join that drives a watchlist-based filter.
            {"name": "watchlist_hits.objectId", "type": "string"},
            {"name": "watchlist_hits.name", "type": "string"},
            {"name": "watchlist_hits.arcsec", "type": "double"},
            {"name": "watchlist_hits.wl_id", "type": "int"},
            {"name": "watchlist_hits.cone_id", "type": "int"},
            {"name": "sherlock_classifications.objectId", "type": "string"},
            {"name": "sherlock_classifications.classification", "type": "string"},
            {"name": "sherlock_classifications.raDeg", "type": "double"},
            {"name": "sherlock_classifications.decDeg", "type": "double"},
            {"name": "sherlock_classifications.distance", "type": "double"},
            {"name": "sherlock_classifications.z", "type": "double"},
            {"name": "crossmatch_tns.tns_name", "type": "string"},
            {"name": "crossmatch_tns.type", "type": "string"},
            {"name": "crossmatch_tns.z", "type": "double"},
            {"name": "crossmatch_tns.host_name", "type": "string"},
        ]
    return {"type": "record", "name": "objects", "fields": fields}


def _token(broker, token=None):
    """The Lasair REST token to act with: a caller's own wins over the broker's
    shared one, so a private filter is read by the account that can see it."""
    token = token or (broker.altdata or {}).get("token")
    if not token:
        raise ValueError("Broker altdata is missing 'token'.")
    return token


def _endpoint(broker):
    return (broker.altdata or {}).get("endpoint", DEFAULT_ENDPOINT)


# Lasair rate-limits per account, and ingestion fetches one object at a time, so
# a busy filter walks straight into 429s. Wait and retry rather than dropping the
# object: the alternative is a cycle that silently ingests a fraction of what it
# matched.
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_PAUSE = 10.0


def _request(broker, method, data, token=None):
    """Call a Lasair REST method: ``POST {endpoint}/{method}/`` with form data and
    a ``Authorization: Token`` header (what the ``lasair`` client does, so no
    dependency). Returns the parsed JSON.

    Retries on 429, honouring ``Retry-After`` when Lasair sends one.
    """
    url = _endpoint(broker).rstrip("/") + "/" + method + "/"
    headers = {"Authorization": f"Token {_token(broker, token)}"}
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        response = requests.post(
            url, data=data, headers=headers, timeout=DEFAULT_TIMEOUT
        )
        if response.status_code != 429 or attempt == RATE_LIMIT_RETRIES:
            response.raise_for_status()
            return response.json()
        try:
            pause = float(response.headers.get("Retry-After", RATE_LIMIT_PAUSE))
        except (TypeError, ValueError):
            pause = RATE_LIMIT_PAUSE
        log(f"Lasair rate-limited ({method}); waiting {pause:.0f}s")
        time.sleep(min(pause, 60.0))
    raise RuntimeError("unreachable")


def _object(broker, object_id, token=None):
    return _request(
        broker,
        "object",
        {"objectId": object_id, "lite": True, "lasair_added": True},
        token=token,
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


def _cutouts_from_object(obj, alert_id):
    """Base64 cutouts from an already-fetched Lasair object. Takes the object
    rather than fetching it: a standard Lasair account gets 100 calls an hour."""
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


async def _ingest_object(broker, oid, survey, filter_ids, token=None):
    """Build the standard alert for one Lasair object, register it as a Candidate
    and save any annotator annotations it carried. Shared by both ingestion modes,
    which differ only in how they learn an objectId."""
    import asyncio

    import sqlalchemy as sa

    from baselayer.app.models import async_plain_session_factory

    from ..models import User
    from ._save import save_object_as_candidate

    obj = await asyncio.to_thread(_object, broker, oid, token)
    data = _normalize_object(obj, oid)
    try:
        cutouts = await asyncio.to_thread(_cutouts_from_object, obj, oid)
    except Exception:
        cutouts = None
    async with async_plain_session_factory() as session:
        user = await session.scalar(sa.select(User).where(User.id == 1))
        await save_object_as_candidate(
            data,
            survey,
            session,
            user,
            filter_ids,
            passing_alert_id=data.get("candidate", {}).get("candid"),
            cutouts=cutouts or None,
        )
        # save_object_as_candidate committed; save annotator data next.
        lasair_annotations = data.get("annotations") or []
        if lasair_annotations:
            await _save_annotator_annotations(
                session, user, oid, filter_ids, lasair_annotations
            )
            await session.commit()


def _object_id_from_message(payload):
    """The objectId carried by a Lasair stream message, under any of the keys
    Lasair uses across its LSST and ZTF deployments."""
    if not isinstance(payload, dict):
        return None
    for key in ("diaObjectId", "objectId", "object", "objectID"):
        value = payload.get(key)
        if isinstance(value, str | int):
            return str(value)
    return None


def _decode_stream_message(value):
    """Decode one Lasair Kafka message. Lasair streams JSON; Avro is accepted so
    a future schema change does not need a new code path."""
    import json as _json

    if value is None:
        return None
    try:
        payload = _json.loads(
            value.decode("utf-8") if isinstance(value, bytes) else value
        )
    except (UnicodeDecodeError, ValueError):
        from ._kafka import read_avro

        payload = read_avro(value)
    # A filter's stream may wrap the row, e.g. {"objectData": {...}}.
    if isinstance(payload, dict) and _object_id_from_message(payload) is None:
        for key in ("objectData", "object", "data"):
            nested = payload.get(key)
            if isinstance(nested, dict) and _object_id_from_message(nested):
                return nested
    return payload


async def _save_annotator_annotations(session, user, obj_id, filter_ids, annotations):
    """Upsert Lasair annotator annotations onto ``obj_id``, scoped to the groups
    of the ingesting filters. Origin is ``"lasair:{topic}"``."""
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from baselayer.app.models import utcnow

    from ..models import Annotation, Filter, GroupAnnotation

    filters = (
        await session.scalars(sa.select(Filter).where(Filter.id.in_(filter_ids)))
    ).all()
    group_ids = list({f.group_id for f in filters if f.group_id})
    if not group_ids:
        return

    for ann in annotations:
        topic = ann.get("topic")
        if not topic:
            continue
        origin = f"lasair:{topic}"
        ann_data = {k: v for k, v in ann.items() if k != "topic"}
        annotation_id = await session.scalar(
            pg_insert(Annotation)
            .values(obj_id=obj_id, origin=origin, data=ann_data, author_id=user.id)
            .on_conflict_do_update(
                index_elements=["obj_id", "origin"],
                set_={"data": ann_data, "modified": utcnow},
                where=Annotation.author_id == user.id,
            )
            .returning(Annotation.id)
        )
        if annotation_id is not None:
            for gid in group_ids:
                await session.execute(
                    pg_insert(GroupAnnotation)
                    .values(group_id=gid, annotation_id=annotation_id)
                    .on_conflict_do_nothing()
                )


def _stream_configured(altdata):
    """Whether the broker's own config selects Lasair's Kafka streams over its SQL
    API. A user's own credentials select streaming too, independently of this."""
    kafka = (altdata or {}).get("kafka") or {}
    return bool(kafka.get("topics") or kafka.get("topic_filter_ids"))


def _credential_sets(broker, extra=None):
    """The Lasair accounts to consume as, one entry per set of credentials.

    A topic is named ``lasair_<account id><filter name>``, so one consumer cannot
    stand in for several accounts: each set carries its own Kafka credentials,
    REST token and topics. ``altdata['kafka']`` is the shared account, ``extra``
    the user-owned ones.
    """
    altdata = broker.altdata or {}
    kafka = altdata.get("kafka") or {}
    shared = {
        "label": "shared",
        "kafka": kafka,
        "token": altdata.get("token"),
        "topics": kafka.get("topics") or [],
        "topic_filter_ids": kafka.get("topic_filter_ids") or {},
        "filter_ids": altdata.get("filter_ids") or [],
    }
    sets = [shared] if (shared["topics"] or shared["topic_filter_ids"]) else []
    for entry in extra or []:
        # Connection details come from the broker; only identity and routing
        # differ per account.
        merged = {**kafka, **(entry.get("kafka") or {})}
        sets.append(
            {
                "label": entry.get("label") or merged.get("username") or "account",
                "kafka": merged,
                "token": entry.get("token"),
                "topics": entry.get("topics") or [],
                "topic_filter_ids": entry.get("topic_filter_ids") or {},
                "filter_ids": entry.get("filter_ids")
                or (altdata.get("filter_ids") or []),
            }
        )
    return sets


async def _consume_set(broker, survey, credentials, budget, stop):
    """Consume one account's topics until `stop` is set or `budget` is spent."""
    import asyncio

    from confluent_kafka import Consumer

    from ._kafka import kafka_consumer_config

    kafka = credentials["kafka"]
    topic_filter_ids = {
        str(k): v for k, v in (credentials["topic_filter_ids"] or {}).items()
    }
    topics = list(dict.fromkeys(list(credentials["topics"]) + list(topic_filter_ids)))
    maxtimeout = float(kafka.get("maxtimeout", 5))

    # A distinct group per account, so the consumers do not split each other's
    # partitions, and a stable one, so offsets survive a restart.
    default_group = f"skyportal-broker-{broker.id}-{credentials['label']}"
    config = kafka_consumer_config(kafka, kafka.get("group_id") or default_group)
    consumer = Consumer(config)
    consumer.subscribe(topics)
    log(
        f"Lasair Kafka ingestion (broker {broker.id}, account "
        f"{credentials['label']}): subscribed to {topics}"
    )

    try:
        while not stop.is_set():
            if budget["remaining"] is not None and budget["remaining"] <= 0:
                stop.set()
                break
            msg = await asyncio.to_thread(consumer.poll, maxtimeout)
            if msg is None or msg.error():
                continue
            filter_ids = topic_filter_ids.get(msg.topic(), credentials["filter_ids"])
            try:
                payload = _decode_stream_message(msg.value())
            except Exception as e:
                log(f"Error decoding Lasair message on {msg.topic()}: {e}")
                continue
            oid = _object_id_from_message(payload)
            if oid is None:
                log(f"Lasair message on {msg.topic()} carried no objectId; skipping")
                continue
            try:
                await _ingest_object(
                    broker, oid, survey, filter_ids, token=credentials["token"]
                )
            except Exception as e:
                log(f"Error ingesting Lasair object {oid}: {e}")
            if budget["remaining"] is not None:
                budget["remaining"] -= 1
    finally:
        consumer.close()


def available_topics(broker, credentials=None):
    """Lasair topics these credentials can actually read. A topic is named
    ``lasair_<account id><filter name>``, so the set differs per account and
    cannot be derived from the filter name alone."""
    from ._kafka import list_topics

    altdata = broker.altdata or {}
    kafka = {**(altdata.get("kafka") or {}), **((credentials or {}).get("kafka") or {})}
    # Metadata only; a distinct group so it never disturbs an ingestion offset.
    topics = list_topics(kafka, f"skyportal-broker-{broker.id}-topics")
    return [t for t in topics if t.startswith("lasair_")]


async def _user_credential_sets(broker):
    """Credential sets from the per-user rows, so a private filter is consumed
    by the account that owns it rather than the broker's shared account."""
    import sqlalchemy as sa

    from baselayer.app.models import async_plain_session_factory

    from ..models import BrokerCredential

    async with async_plain_session_factory() as session:
        rows = (
            await session.scalars(
                sa.select(BrokerCredential).where(
                    BrokerCredential.broker_id == broker.id
                )
            )
        ).all()
        # Only an account with topics has anything to consume; skip the rest so
        # a stored credential does not cost an idle connection.
        return [r.as_credential_set() for r in rows if r.topics]


async def _run_kafka_ingestion(
    broker, survey, stop=None, max_messages=None, credentials=None
):
    """Consume Lasair's per-filter Kafka streams and register each object as a
    Candidate, one consumer per account.

    A message only has to carry an objectId: the object, photometry, cutouts and
    annotator data are fetched through the REST API with that account's token,
    the same path the SQL poller uses. ``credentials`` pins the accounts to
    consume; by default the stored ones, re-read every
    ``CREDENTIAL_RESCAN_INTERVAL`` so a user registering an account is picked up
    without restarting the service.
    """
    import asyncio

    stop = stop or asyncio.Event()
    # Shared so max_messages bounds the run, not each consumer separately.
    budget = {"remaining": max_messages}
    running = {}
    retiring = []
    started = False

    def spent():
        return budget["remaining"] is not None and budget["remaining"] <= 0

    def failed(label, task):
        if not task.done() or task.cancelled() or task.exception() is None:
            return False
        log(f"Lasair consumer for account {label} crashed: {task.exception()}")
        return True

    try:
        while not stop.is_set() and not spent():
            extra = (
                credentials
                if credentials is not None
                else await _user_credential_sets(broker)
            )
            sets = {c["label"]: c for c in _credential_sets(broker, extra)}
            if not sets:
                if started:
                    return
                raise ValueError(
                    "Lasair Kafka ingestion requires topics, on the broker's "
                    "altdata['kafka'] or on a user's own credentials."
                )
            for label in [lb for lb in running if lb not in sets]:
                task, account_stop = running.pop(label)
                account_stop.set()
                retiring.append((label, task))
            retiring = [
                (lb, t) for lb, t in retiring if not failed(lb, t) and not t.done()
            ]
            for label, account in sets.items():
                task = running.get(label, (None, None))[0]
                if task is None or task.done():
                    account_stop = asyncio.Event()
                    running[label] = (
                        asyncio.create_task(
                            _consume_set(broker, survey, account, budget, account_stop)
                        ),
                        account_stop,
                    )
            started = True
            waiter = asyncio.ensure_future(stop.wait())
            try:
                await asyncio.wait(
                    [
                        waiter,
                        *(t for t, _ in running.values()),
                        *(t for _, t in retiring),
                    ],
                    timeout=CREDENTIAL_RESCAN_INTERVAL,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                waiter.cancel()
            crashed = [lb for lb, (task, _) in running.items() if failed(lb, task)]
            # Restarting a consumer that fails on connect must not busy-loop.
            if crashed and not stop.is_set():
                await asyncio.sleep(CONSUMER_RETRY_PAUSE)
    finally:
        for _, account_stop in running.values():
            account_stop.set()
        await asyncio.gather(
            *(t for t, _ in running.values()),
            *(t for _, t in retiring),
            return_exceptions=True,
        )


class LASAIRBROKER(BrokerAPI):
    """The Lasair broker (https://lasair.lsst.ac.uk).

    Interactive access via Lasair's REST API (called directly with ``requests``,
    no client dependency). Configure a ``Broker`` with ``altdata = {"token":
    "...", "endpoint": "..."}`` (endpoint defaults to the LSST instance).
    """

    surveys = ["ZTF", "LSST"]
    filter_kind = "query"

    @classmethod
    def configured_surveys(cls, altdata):
        # Lasair's ZTF and LSST are separate deployments (distinct endpoint +
        # token), so a record serves exactly one, derived from its config.
        return [_survey_from_altdata(altdata)]

    form_json_schema_config = {
        "type": "object",
        "required": ["endpoint"],
        "properties": {
            "token": {
                "type": "string",
                "title": "Lasair API token",
                "description": "Your Lasair API token (40 hex characters).",
            },
            "endpoint": {
                "type": "string",
                "title": "API endpoint",
                "default": DEFAULT_ENDPOINT,
                "description": (
                    "Lasair API base URL. LSST instance: "
                    "https://api.lasair.lsst.ac.uk/api ; ZTF instance: "
                    "https://lasair-ztf.lsst.ac.uk/api . These are separate "
                    "systems with separate tokens."
                ),
            },
            "survey": {
                "type": "string",
                "enum": ["ZTF", "LSST"],
                "title": "Survey",
                "description": (
                    "Survey this connection serves. Leave unset to infer it "
                    "from the endpoint."
                ),
            },
            "poll_interval": {
                "type": "number",
                "title": "Poll interval (seconds)",
                "default": 86400,
                "description": (
                    "How often this broker's filters are re-run against Lasair. "
                    "Default 86400 (once per day)."
                ),
            },
            "limit": {
                "type": "integer",
                "title": "Max results per query",
                "default": 1000,
                "description": "Maximum objects returned per Lasair query.",
            },
            "kafka": {
                "type": "object",
                "title": "Kafka stream (optional)",
                "description": (
                    "Consume Lasair's per-filter streams instead of polling its "
                    "SQL API. Setting topics or topic_filter_ids switches this "
                    "broker to streaming; leave empty to keep polling."
                ),
                "properties": {
                    "host": {
                        "type": "string",
                        "title": "Kafka host",
                        "default": "lasair-lsst-kafka_pub.lsst.ac.uk",
                        "description": (
                            "Lasair Kafka broker host. The LSST instance's public "
                            "stream is lasair-lsst-kafka_pub.lsst.ac.uk:9092, which "
                            "needs no credentials -- the API token is still needed "
                            "to fetch each object."
                        ),
                    },
                    "port": {
                        "type": "integer",
                        "title": "Kafka port",
                        "default": 9092,
                    },
                    "group_id": {
                        "type": "string",
                        "title": "Consumer group id",
                        "description": (
                            "Defaults to skyportal-broker-<id>. Lasair resumes a "
                            "known group from its last delivered alert; a new group "
                            "replays the 7-day cache, so keep this stable."
                        ),
                    },
                    "username": {"type": "string", "title": "SASL username"},
                    "password": {"type": "string", "title": "SASL password"},
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "title": "Topics",
                        "description": (
                            "Lasair topics to consume. A topic is one of your "
                            "Lasair filters, named lasair_<account id><filter "
                            "name>, e.g. lasair_2Hasabsmag. Objects from a topic "
                            "not listed in the routing map below become candidates "
                            "under the broker-wide filter_ids."
                        ),
                    },
                    "topic_filter_ids": {
                        "type": "object",
                        "title": "Topic -> filter ids",
                        "description": (
                            "Route each topic to the skyportal Filters its objects "
                            "become candidates for, e.g. "
                            '{"lasair_2SN-likecandidates": [1234]}.'
                        ),
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "maxtimeout": {
                        "type": "number",
                        "title": "Poll timeout (seconds)",
                        "default": 5,
                    },
                    "auto_offset_reset": {
                        "type": "string",
                        "enum": ["earliest", "latest"],
                        "default": "earliest",
                        "title": "Start position for a new consumer group",
                    },
                },
            },
        },
    }

    # A Lasair account owns its filters, and a private one is visible to nobody
    # else, so these are per user rather than per broker.
    user_credential_schema = {
        "type": "object",
        "properties": {
            "token": {
                "type": "string",
                "title": "Lasair API token",
                "description": (
                    "Your own token, from your Lasair profile. Used to read the "
                    "objects your filters match."
                ),
            },
            "username": {
                "type": "string",
                "title": "SASL username",
                "description": "Only for a stream that requires authentication.",
            },
            "password": {
                "type": "string",
                "title": "SASL password",
                "description": "Only for a stream that requires authentication.",
            },
        },
    }

    user_credential_ui_schema = {
        "token": {"ui:widget": "password"},
        "password": {"ui:widget": "password"},
    }

    ui_json_schema = {
        "token": {"ui:widget": "password"},
        "kafka": {"password": {"ui:widget": "password"}},
    }

    @staticmethod
    def validate_config(altdata):
        if not (altdata or {}).get("endpoint"):
            raise ValueError("Broker altdata must include 'endpoint'.")

    @staticmethod
    def test_connection(broker):
        _cone(broker, 0, 0, radius=1)

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
        return {elements: altdata_filter_modules(broker, elements, kwargs.get("name"))}

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
        return _cutouts_from_object(_object(broker, alert_id), alert_id)

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Ingest from Lasair, by Kafka stream when one is configured and by
        polling its SQL API otherwise.

        Polling mode: run each configured SQL query, and for every returned
        object reuse this provider's own ``get_alert``/``get_cutouts`` to build the
        standard alert, then register a Candidate under ``filter_ids``. Config in
        ``broker.altdata``: ``queries`` (list of {name, fields, tables, conditions,
        [filter_ids]}), ``filter_ids``, ``survey``, ``poll_interval``, ``limit``.
        """
        import asyncio

        import sqlalchemy as sa

        from baselayer.app.models import async_plain_session_factory

        from ..models import Filter

        altdata = broker.altdata or {}
        survey = _survey(broker)
        # Kafka when a stream is configured, otherwise the SQL poller. A topic is
        # a Lasair filter, so the stream is live where the poller is per-interval.
        if _stream_configured(altdata) or await _user_credential_sets(broker):
            return await _run_kafka_ingestion(
                broker, survey, stop=stop, max_messages=max_messages
            )
        default_filter_ids = altdata.get("filter_ids") or []
        legacy_queries = altdata.get("queries") or []
        poll_interval = float(altdata.get("poll_interval", 86400))
        limit = int(altdata.get("limit", 1000))

        def _stopped():
            return stop is not None and stop.is_set()

        async def _collect_queries():
            # One query per skyportal Filter attached to this broker (its saved
            # SQL lives in Filter.altdata["lasair"]), plus any legacy queries on
            # the broker record. Re-read each cycle so filter edits are picked up.
            async with async_plain_session_factory() as session:
                rows = (
                    await session.scalars(
                        sa.select(Filter).where(Filter.broker_id == broker.id)
                    )
                ).all()
            queries = []
            for f in rows:
                ad = f.altdata if isinstance(f.altdata, dict) else {}
                lasair = ad.get("lasair") if isinstance(ad, dict) else None
                if not isinstance(lasair, dict):
                    continue
                if not lasair.get("tables"):
                    continue
                queries.append(
                    {
                        "name": f.name,
                        "fields": lasair.get("selected") or lasair.get("fields"),
                        "tables": lasair["tables"],
                        "conditions": lasair.get("conditions", ""),
                        "filter_ids": [f.id],
                    }
                )
            return queries + legacy_queries

        count = 0
        # A broker with nothing to poll otherwise looks identical to a broken
        # one: the loop just sleeps. Say so once, and again if it recurs.
        warned_no_queries = False
        while not _stopped():
            queries = await _collect_queries()
            if not queries:
                if not warned_no_queries:
                    log(
                        f"Lasair broker {broker.id} has no queries to poll: attach "
                        "a filter to it with a saved Lasair query (selected/tables), "
                        "or set 'queries' in the broker's altdata."
                    )
                    warned_no_queries = True
            else:
                warned_no_queries = False

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
                        await _ingest_object(broker, oid, survey, filter_ids)
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
