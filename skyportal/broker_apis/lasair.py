import asyncio
import base64
import json
import math
import time

import numpy as np
import requests
import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.log import make_log

from ..utils.cache import Cache, cache_folder, dict_to_bytes
from .interface import BrokerAPI, altdata_filter_modules

log = make_log("broker/lasair")

env, cfg = load_env()

# A Lasair account is allowed 100 API calls an hour, and the cutouts of an
# object do not change, so a fetched set is kept and reused rather than asking
# again for an object we already have.
cutouts_cache = Cache(
    cache_dir=f"{cache_folder}/broker_cutouts",
    max_age=cfg.get("misc.minutes_to_keep_broker_cutouts_cache", 1440) * 60,
)

DEFAULT_ENDPOINT = "https://api.lasair.lsst.ac.uk/api"
DEFAULT_TIMEOUT = 30
CREDENTIAL_RESCAN_INTERVAL = 60
CONSUMER_RETRY_PAUSE = 5
CONSUMER_MAX_RETRY_PAUSE = 300
PROGRESS_INTERVAL = 300
# Messages polled at once, and how many are ingested in parallel. Each ingest is
# a database round trip, so one at a time leaves the consumer waiting on the DB.
INGEST_BATCH = 50
INGEST_CONCURRENCY = 8
_CUTOUT_KINDS = {
    "Science": "cutoutScience",
    "Template": "cutoutTemplate",
    "Difference": "cutoutDifference",
}
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}
MJD_TO_JD = 2400000.5
# LSST reports difference-image fluxes in nJy; AB mag = -2.5 log10(f/3631 Jy),
# which for nJy is this zeropoint.
LSST_FLUX_ZEROPOINT = 31.4


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


def _lsst_magnitude(flux, flux_err):
    """AB magnitude and error from an LSST psfFlux in nJy.

    A difference-image flux at or below zero is a non-detection, which carries
    no magnitude: returning one would turn a non-detection into a measurement.
    """
    try:
        flux = float(flux)
    except (TypeError, ValueError):
        return None, None
    if flux <= 0:
        return None, None
    mag = LSST_FLUX_ZEROPOINT - 2.5 * math.log10(flux)
    try:
        err = abs(2.5 / math.log(10) * float(flux_err) / flux)
    except (TypeError, ValueError, ZeroDivisionError):
        err = None
    return mag, err


def _lsst_sources(payload):
    """The diaSources a Lasair LSST record carries, if any.

    The REST object holds them at the top level; a Kafka topic on
    lite_lightcurve or full nests them under ``alert``. A topic streaming object
    ids alone carries neither.
    """
    if not isinstance(payload, dict):
        return []
    for container in (payload, payload.get("alert")):
        if isinstance(container, dict):
            sources = container.get("diaSourcesList")
            if isinstance(sources, list) and sources:
                return sources
    return []


def _normalize_lsst_alert(payload, object_id):
    """Standard alert shape from a Lasair LSST stream message.

    LSST names and units differ throughout: fluxes in nJy rather than
    magnitudes, MJD(TAI) rather than JD, ``decl`` rather than ``dec``.
    Forced photometry travels beside the detections under
    ``diaForcedSourcesList`` and is left for the caller that wants limits.
    """
    alert = payload.get("alert") if isinstance(payload.get("alert"), dict) else {}
    dia_object = payload.get("diaObject") or alert.get("diaObject") or {}
    rows = []
    for source in _lsst_sources(payload):
        if not isinstance(source, dict):
            continue
        mjd = source.get("midpointMjdTai")
        if mjd is None:
            continue
        mag, magerr = _lsst_magnitude(source.get("psfFlux"), source.get("psfFluxErr"))
        rows.append(
            {
                "jd": float(mjd) + MJD_TO_JD,
                "magpsf": mag,
                "sigmapsf": magerr,
                "band": source.get("band"),
                "ra": source.get("ra"),
                "dec": source.get("dec", source.get("decl")),
                # A live diaSource carries no id, and a null passing_alert_id
                # defeats the candidate de-duplication (SQL "= NULL" matches
                # nothing), so the epoch stands in: it is stable per object and
                # alert, which is what the de-duplication keys on.
                "candid": source.get("diaSourceId")
                if source.get("diaSourceId") is not None
                else int(round(float(mjd) * 1e6)),
            }
        )
    rows.sort(key=lambda r: r["jd"], reverse=True)
    detections = [r for r in rows if r["magpsf"] is not None]
    latest = detections[0] if detections else (rows[0] if rows else {})

    def position(key, *fallbacks):
        for source in (latest, payload, dia_object):
            for name in (key, *fallbacks):
                value = (source or {}).get(name)
                if value is not None:
                    return value
        return None

    return {
        "objectId": str(
            payload.get("diaObjectId") or dia_object.get("diaObjectId") or object_id
        ),
        "candidate": {
            "candid": latest.get("candid"),
            "ra": position("ra"),
            "dec": position("dec", "decl"),
            "magpsf": latest.get("magpsf"),
            "jd": latest.get("jd"),
            "band": latest.get("band"),
        },
        "prv_candidates": [
            {k: r[k] for k in ("jd", "magpsf", "sigmapsf", "band", "ra", "dec")}
            for r in detections
        ],
        "annotations": [],
    }


def _normalize_object(obj, object_id):
    """Reshape a Lasair object into the standard alert shape the rest of the
    stack consumes: ``{objectId, candidate, prv_candidates, annotations}``.

    The two instances return different records, so the LSST one is recognised by
    its diaSources and reshaped separately.
    """
    if _lsst_sources(obj):
        return _normalize_lsst_alert(obj, object_id)
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
                    classdict = json.loads(classdict)
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
    token = token or (broker.altdata or {}).get("token")
    if not token:
        raise ValueError("Broker altdata is missing 'token'.")
    return token


def _endpoint(broker):
    return (broker.altdata or {}).get("endpoint", DEFAULT_ENDPOINT)


RATE_LIMIT_RETRIES = 3
RATE_LIMIT_PAUSE = 10.0


def _parse_json(response):
    """Parse a Lasair response, tolerating the bare ``NaN`` it emits.

    LSST records carry ``NaN`` for unmeasured values (``dipoleAngle``, and
    others), which is not a JSON value. The standard library accepts it as an
    extension, but ``response.json()`` defers to simplejson when that is
    installed and rejects it, so every LSST object fetch raises. NaN becomes
    None here rather than a float, since it travels on into JSON columns.
    """
    return json.loads(response.text, parse_constant=lambda _: None)


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
            return _parse_json(response)
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


def _cached_cutouts(broker, obj, alert_id):
    """Cutouts for an object, fetched once and reused.

    The images are keyed by object because Lasair keys them that way, so every
    later alert on the same object is served from the cache instead of costing
    an API call out of the hundred an hour.
    """
    key = f"{broker.id}_{alert_id}"
    cached = cutouts_cache[key]
    if cached is not None:
        try:
            return np.load(cached, allow_pickle=True).item()["cutouts"]
        except Exception:
            log(f"unreadable cutout cache entry for {key}, refetching")
    cutouts = _cutouts_from_object(obj, alert_id)
    if cutouts:
        cutouts_cache[key] = dict_to_bytes({"cutouts": cutouts})
    return cutouts


def _cutouts_from_object(obj, alert_id):
    """Base64 cutouts from an already-fetched Lasair object, so an ingest that
    holds one does not spend a second call: a Lasair account gets 100 an hour."""
    # ZTF carries image_urls on the latest candidate, LSST lasairData.imageUrls.
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


def carries_lightcurve(payload):
    """Whether a stream message already holds the photometry we would otherwise
    fetch. ZTF carries ``candidates``; LSST nests ``diaSourcesList`` under
    ``alert``. A topic streaming object ids alone has neither, and only those
    need the REST call."""
    if not isinstance(payload, dict):
        return False
    candidates = payload.get("candidates")
    if isinstance(candidates, list) and candidates:
        return True
    return bool(_lsst_sources(payload))


def normalize_stream_message(payload, object_id):
    """Standard alert shape from a stream message, whichever instance sent it."""
    return _normalize_object(payload, object_id)


async def _ingest_object(broker, oid, survey, filter_ids, token=None, payload=None):
    """Build the standard alert for one Lasair object, register it as a Candidate
    and save any annotator annotations it carried. Shared by both ingestion modes,
    which differ only in how they learn an objectId.

    The REST call is made only when the caller has no object in hand: a Lasair
    account is allowed on the order of 100 calls an hour, far below the rate of
    the stream it is reading.
    """
    from baselayer.app.models import async_plain_session_factory

    from ..models import Thumbnail, User
    from ._save import save_object_as_candidate

    if carries_lightcurve(payload):
        obj = payload
    else:
        obj = await asyncio.to_thread(_object, broker, oid, token)
    data = _normalize_object(obj, oid)
    async with async_plain_session_factory() as session:
        user = await session.scalar(sa.select(User).where(User.id == 1))
        # Cutouts are stored once per object, so an object already carrying
        # thumbnails does not re-download them on every alert.
        cutouts = None
        has_thumbnails = await session.scalar(
            sa.select(sa.exists().where(Thumbnail.obj_id == oid))
        )
        if not has_thumbnails:
            try:
                cutouts = await asyncio.to_thread(_cached_cutouts, broker, obj, oid)
            except Exception:
                cutouts = None
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
    if value is None:
        return None
    try:
        payload = json.loads(
            value.decode("utf-8") if isinstance(value, bytes) else value
        )
    except (UnicodeDecodeError, ValueError):
        from ._kafka import read_avro

        payload = read_avro(value)
    if isinstance(payload, dict) and _object_id_from_message(payload) is None:
        for key in ("objectData", "object", "data"):
            nested = payload.get(key)
            if isinstance(nested, dict) and _object_id_from_message(nested):
                return nested
    return payload


async def _save_annotator_annotations(session, user, obj_id, filter_ids, annotations):
    """Upsert Lasair annotator annotations onto ``obj_id``, scoped to the groups
    of the ingesting filters. Origin is ``"lasair:{topic}"``."""
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


def _prepare_batch(msgs, topic_filter_ids, default_filter_ids):
    """Split a polled batch into work to do and messages that need none.

    A message that cannot be decoded, or that carries no objectId, is finished
    rather than failed: leaving it outstanding would stall its partition for
    good. Where one object appears more than once, only its newest alert is
    ingested and the earlier ones are finished, which also keeps two writes for
    the same object out of the same batch.
    """
    finished = set()
    work = {}
    for msg in msgs:
        key = (msg.topic(), msg.partition(), msg.offset())
        if msg.error():
            finished.add(key)
            continue
        try:
            payload = _decode_stream_message(msg.value())
        except Exception as e:
            log(f"Error decoding Lasair message on {msg.topic()}: {e}")
            finished.add(key)
            continue
        oid = _object_id_from_message(payload)
        if oid is None:
            log(f"Lasair message on {msg.topic()} carried no objectId; skipping")
            finished.add(key)
            continue
        superseded = work.get(oid)
        if superseded is not None:
            older = superseded[0]
            finished.add((older.topic(), older.partition(), older.offset()))
        work[oid] = (
            msg,
            payload,
            topic_filter_ids.get(msg.topic(), default_filter_ids),
        )
    return finished, work


async def _ingest_batch(broker, survey, token, work, concurrency):
    """Ingest a batch, at most `concurrency` at a time. Returns {key: succeeded}."""
    semaphore = asyncio.Semaphore(concurrency)

    async def run(oid, msg, payload, filter_ids):
        async with semaphore:
            try:
                await _ingest_object(
                    broker, oid, survey, filter_ids, token=token, payload=payload
                )
                return True
            except Exception as e:
                log(f"Error ingesting Lasair object {oid}: {e}")
                return False

    items = list(work.items())
    outcomes = await asyncio.gather(
        *(run(oid, msg, payload, fids) for oid, (msg, payload, fids) in items)
    )
    return {
        (msg.topic(), msg.partition(), msg.offset()): ok
        for (_oid, (msg, _p, _f)), ok in zip(items, outcomes, strict=True)
    }


def _store_batch_offsets(consumer, msgs, finished, results):
    """Store each partition's offsets up to its first failure.

    Storing past one would acknowledge an alert that was never ingested, which
    is the loss that committing on a timer used to cause.
    """
    by_partition = {}
    for msg in msgs:
        by_partition.setdefault((msg.topic(), msg.partition()), []).append(msg)
    for partition_msgs in by_partition.values():
        storable = None
        for msg in sorted(partition_msgs, key=lambda m: m.offset()):
            key = (msg.topic(), msg.partition(), msg.offset())
            if key in finished or results.get(key):
                storable = msg
                continue
            break
        if storable is not None:
            consumer.store_offsets(message=storable)


def _consumer_lag(consumer):
    """Messages behind the head of the stream, summed over assigned partitions.

    Falling behind otherwise looks exactly like a quiet stream: both deliver
    nothing. Returns ``"unknown"`` when the broker will not answer, since the
    figure is for a log line and must never stop ingestion.
    """
    try:
        total = 0
        for partition in consumer.assignment():
            position = consumer.position([partition])[0].offset
            _, high = consumer.get_watermark_offsets(partition, timeout=2.0)
            if position is not None and position >= 0 and high is not None:
                total += max(0, high - position)
        return total
    except Exception:
        return "unknown"


async def _consume_set(broker, survey, credentials, budget, stop):
    """Consume one account's topics until `stop` is set or `budget` is spent."""
    from confluent_kafka import Consumer

    from ._kafka import kafka_consumer_config

    kafka = credentials["kafka"]
    topic_filter_ids = {
        str(k): v for k, v in (credentials["topic_filter_ids"] or {}).items()
    }
    topics = list(dict.fromkeys(list(credentials["topics"]) + list(topic_filter_ids)))
    maxtimeout = float(kafka.get("maxtimeout", 5))

    # Suffixed per account: a shared group drives another account's offsets.
    base = kafka.get("group_id") or f"skyportal-broker-{broker.id}"
    group = f"{base}-{credentials['label']}"
    config = kafka_consumer_config({**kafka, "group_id": group}, group)
    # Auto-commit still runs, but only over offsets we store, and we store one
    # after it has been ingested: on the default a crash acknowledges whatever
    # the five-second timer had reached and those alerts are never seen again.
    config["enable.auto.offset.store"] = False
    consumer = Consumer(config)
    consumer.subscribe(topics)
    log(
        f"Lasair Kafka ingestion (broker {broker.id}, account "
        f"{credentials['label']}): subscribed to {topics}"
    )
    ingested = 0
    last_report = time.monotonic()
    batch_size = max(1, int(kafka.get("batch_size", INGEST_BATCH)))
    concurrency = max(1, int(kafka.get("concurrency", INGEST_CONCURRENCY)))

    try:
        while not stop.is_set():
            if budget["remaining"] is not None and budget["remaining"] <= 0:
                stop.set()
                break
            wanted = batch_size
            if budget["remaining"] is not None:
                wanted = max(1, min(wanted, budget["remaining"]))
            msgs = await asyncio.to_thread(consumer.consume, wanted, maxtimeout)
            if not msgs:
                continue
            finished, work = _prepare_batch(
                msgs, topic_filter_ids, credentials["filter_ids"]
            )
            results = await _ingest_batch(
                broker, survey, credentials["token"], work, concurrency
            )
            _store_batch_offsets(consumer, msgs, finished, results)
            ingested += sum(1 for ok in results.values() if ok)

            now = time.monotonic()
            if now - last_report >= PROGRESS_INTERVAL:
                log(
                    f"Lasair Kafka ingestion (broker {broker.id}, account "
                    f"{credentials['label']}): {ingested} ingested in the last "
                    f"{now - last_report:.0f}s, lag {_consumer_lag(consumer)}"
                )
                ingested, last_report = 0, now
            if budget["remaining"] is not None:
                budget["remaining"] -= len(msgs)
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
        return [r.as_credential_set() for r in rows if r.topics]


async def _run_kafka_ingestion(
    broker, survey, stop=None, max_messages=None, credentials=None
):
    """Consume Lasair's per-filter Kafka streams and register each object as a
    Candidate, one consumer per account.

    A topic carrying the lightcurve (``lite_lightcurve`` or ``full``) is ingested
    from the message itself. A message holding only an objectId is completed
    through the REST API with that account's token, the same path the SQL poller
    uses; that call is rate-limited by Lasair well below stream rate, so it runs
    only when the message is not enough on its own. ``credentials`` pins the
    accounts to consume; by default the stored ones, re-read every
    ``CREDENTIAL_RESCAN_INTERVAL`` so a user registering an account is picked up
    without restarting the service.
    """
    stop = stop or asyncio.Event()
    # Shared so max_messages bounds the run, not each consumer separately.
    budget = {"remaining": max_messages}
    running = {}
    stops = {}
    retiring = []
    failures = {}
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
                stops.pop(label).set()
                retiring.append((label, running.pop(label)))
            retiring = [
                (lb, t) for lb, t in retiring if not failed(lb, t) and not t.done()
            ]
            for label, account in sets.items():
                if label not in running or running[label].done():
                    stops[label] = asyncio.Event()
                    running[label] = asyncio.create_task(
                        _consume_set(broker, survey, account, budget, stops[label])
                    )
            started = True
            waiter = asyncio.ensure_future(stop.wait())
            try:
                await asyncio.wait(
                    [waiter, *running.values(), *(t for _, t in retiring)],
                    timeout=CREDENTIAL_RESCAN_INTERVAL,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                waiter.cancel()
            crashed = [lb for lb, task in running.items() if failed(lb, task)]
            failures = {lb: failures.get(lb, 0) + 1 for lb in crashed}
            # Restarting a consumer that fails on connect must not busy-loop.
            if crashed and not stop.is_set():
                await asyncio.sleep(
                    min(
                        CONSUMER_RETRY_PAUSE * 2 ** (max(failures.values()) - 1),
                        CONSUMER_MAX_RETRY_PAUSE,
                    )
                )
    finally:
        for account_stop in stops.values():
            account_stop.set()
        await asyncio.gather(
            *running.values(), *(t for _, t in retiring), return_exceptions=True
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
    def parallel_ingestion(cls, altdata):
        """Whether extra broker_ingest processes may run this broker.

        A Kafka stream may: the consumer group rebalances its partitions across
        them. The REST poller may not, since each process would spend the same
        account's quota again, so this is false until a stream is configured.
        """
        return bool(_stream_configured(altdata))

    @classmethod
    def configured_surveys(cls, altdata):
        return [_survey_from_altdata(altdata)]

    @staticmethod
    def available_topics(broker, credentials=None):
        return available_topics(broker, credentials)

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
                            "Prefix, suffixed with the account (defaults to "
                            "skyportal-broker-<id>). Lasair resumes a known group "
                            "from its last delivered alert; a new group replays the "
                            "7-day cache, so keep this stable."
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
        """Run a Lasair SQL query and return the matching rows. Accepts raw
        ``conditions`` (SQL) or the builder's neutral ``tree``, compiled here."""
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
            if isinstance(tree, list):
                tree = {"operator": "and", "children": tree}
            conditions = _compile_tree_to_sql(tree)
        else:
            conditions = kwargs.get("conditions") or ""
        limit = int(kwargs.get("limit", 50))
        return _query(broker, selected, tables, conditions, limit=limit)

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        # Lasair keys cutouts by object, not candid, so alert_id is an objectId.
        # A cached set answers without fetching the object, which is what makes
        # this cheap: the object call and the three image fetches both go away.
        key = f"{broker.id}_{alert_id}"
        cached = cutouts_cache[key]
        if cached is not None:
            try:
                return np.load(cached, allow_pickle=True).item()["cutouts"]
            except Exception:
                log(f"unreadable cutout cache entry for {key}, refetching")
        return _cached_cutouts(broker, _object(broker, alert_id), alert_id)

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
        from baselayer.app.models import async_plain_session_factory

        from ..models import Filter

        altdata = broker.altdata or {}
        survey = _survey(broker)
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
            """One query per Filter attached to this broker (its SQL lives in
            ``Filter.altdata["lasair"]``) plus the broker's legacy queries."""
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
                break
            slept = 0.0
            while slept < poll_interval and not _stopped():
                await asyncio.sleep(min(5.0, poll_interval - slept))
                slept += 5.0
        log(f"Lasair ingestion (broker {broker.id}): ingested {count} objects")
        return count
