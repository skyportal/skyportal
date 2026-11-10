import asyncio
import json
import math
import re
import time
from datetime import UTC, datetime

import requests
import sqlalchemy as sa

from baselayer.log import make_log

from .interface import BrokerAPI, altdata_filter_modules

log = make_log("broker/lasair")

ALERTS_BROKER_CLASSES = ("BOOMBROKER", "BABAMULBROKER")
PUBLIC_PERMISSIONS = {"ZTF": [1], "LSST": [1]}

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
# Which stream a Lasair filter sends is the user's choice on the filter's own
# page, and only one of the three choices carries the photometry we need.
PLAIN_STREAM_DETAIL = (
    "This topic streams its Lasair filter's selected columns only, so its "
    "alerts arrive without photometry and cannot be ingested. Set the filter's "
    "streaming choice to 'lite lightcurve' or 'full alert' on its page in "
    "Lasair: https://lasair-lsst.readthedocs.io/en/main/ (ZTF: "
    "https://lasair.readthedocs.io/en/main/)"
)
NO_POSITION_DETAIL = (
    "This topic's alerts carry no sky position. A lite lightcurve reports one "
    "only through its Lasair filter's selected columns, so add the object's ra "
    "and dec to that filter's SELECT on its page in Lasair: "
    "https://lasair-lsst.readthedocs.io/en/main/ (ZTF: "
    "https://lasair.readthedocs.io/en/main/)"
)
# The position keys a message may use, normalized. A filter names its own
# selected columns, so the same coordinate arrives as "ra", "RA" or "ramean".
_RA_KEYS = ("ra", "ramean", "radeg", "rightascension")
_DEC_KEYS = ("dec", "decl", "decmean", "decdeg", "declination")
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


def _site(broker):
    host = "lasair-ztf" if _survey(broker) == "ZTF" else "lasair"
    return f"https://{host}.lsst.ac.uk"


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


def _position(places, keys):
    """First numeric value any of `places` holds under one of `keys`.

    Keys match on their letters and digits alone, so a filter whose selected
    columns came through as ``RA`` and ``Dec`` is still understood.
    """
    for place in places:
        if not isinstance(place, dict):
            continue
        found = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in place.items()}
        for key in keys:
            value = found.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


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

    places = (latest, payload, dia_object)

    return {
        "objectId": str(
            payload.get("diaObjectId") or dia_object.get("diaObjectId") or object_id
        ),
        "candidate": {
            "candid": latest.get("candid"),
            "ra": _position(places, _RA_KEYS),
            "dec": _position(places, _DEC_KEYS),
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
            "isdiffpos": c.get("isdiffpos"),
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
            "ra": _position((latest, object_data), _RA_KEYS),
            "dec": _position((latest, object_data), _DEC_KEYS),
            "magpsf": latest.get("magpsf"),
            "jd": latest.get("jd"),
            "band": _band(latest),
        },
        "prv_candidates": prv_candidates,
        "annotations": annotations,
    }


_SQL_OPS = {"$eq": "=", "$ne": "!=", "$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}


_RELATIVE_MJD = re.compile(r"mjdnow\(\)\s*(?:[-+]\s*\d+(?:\.\d+)?)?")


def _sql_value(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if _RELATIVE_MJD.fullmatch(str(v).strip()):
        return str(v).strip()
    return "'" + str(v).replace("'", "''") + "'"


def _compile_tree_to_sql(node):
    """Compile the builder's neutral condition tree (blocks of AND/OR + field/
    operator/value conditions, the same shape BOOM compiles to a Mongo pipeline)
    into a Lasair SQL WHERE clause."""
    if not isinstance(node, dict):
        return ""
    if node.get("category") == "block" or "children" in node:
        joiner = (node.get("logic") or node.get("operator") or "and").upper()
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


_DEFAULT_SELECTED = {
    "LSST": "objects.diaObjectId, objects.ra, objects.decl",
    "ZTF": "objects.objectId, objects.ramean, objects.decmean",
}


def _tree_fields(node):
    if not isinstance(node, dict):
        return []
    if node.get("category") == "block" or "children" in node:
        return [f for c in node.get("children") or [] for f in _tree_fields(c)]
    field = node.get("field")
    field = field.get("name") if isinstance(field, dict) else field
    return [field] if field else []


def compile_tree(tree, survey):
    if isinstance(tree, list):
        tree = tree[0] if len(tree) == 1 else {"operator": "and", "children": tree}
    fields = list(dict.fromkeys(_tree_fields(tree)))
    base = _DEFAULT_SELECTED.get(survey, _DEFAULT_SELECTED["LSST"])
    tables = ["objects"] + [f.split(".")[0] for f in fields if "." in f]
    extra = [f for f in fields if f not in base.split(", ")]
    return {
        "selected": ", ".join([base, *extra]),
        "tables": ", ".join(dict.fromkeys(tables)),
        "conditions": _compile_tree_to_sql(tree),
    }


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


def _cone(broker, ra, dec, radius=5, request_type="all", token=None):
    return _request(
        broker,
        "cone",
        {"ra": ra, "dec": dec, "radius": radius, "requestType": request_type},
        token=token,
    )


def _query(broker, selected, tables, conditions, limit=1000, token=None):
    return _request(
        broker,
        "query",
        {
            "selected": selected,
            "tables": tables,
            "conditions": conditions,
            "limit": limit,
        },
        token=token,
    )


def _publish(broker, name, query, token=None):
    return _request(
        broker,
        "filters/create",
        {
            "name": name,
            "selected": query["selected"],
            "tables": query["tables"],
            "conditions": query["conditions"],
            "active": 2,
        },
        token=token,
    )


def _alerts_broker(survey):
    """The BOOM (or babamul) broker Lasair objects are read from, so Lasair is
    never asked for an object or its images."""
    from baselayer.app.models import new_session

    from ..models import Broker

    with new_session() as session:
        rows = session.scalars(
            sa.select(Broker)
            .where(
                Broker.active.is_(True),
                Broker.broker_classname.in_(ALERTS_BROKER_CLASSES),
            )
            .order_by(Broker.default_photometry.desc(), Broker.id)
        ).all()
        for row in rows:
            if survey in row.broker_class.configured_surveys(row.altdata):
                session.expunge(row)
                return row
    raise ValueError(f"No active BOOM or babamul broker serves {survey} alerts.")


def _from_alerts_broker(object_id, survey, cutouts=True):
    """The object's alert as BOOM holds it, and its cutouts when asked for.
    Raises LookupError when BOOM has no alert for it."""
    source = _alerts_broker(survey)
    kwargs = {"survey": survey, "permissions": PUBLIC_PERMISSIONS}
    try:
        data = source.broker_class.get_alert(source, object_id, None, **kwargs)
    except requests.HTTPError as e:
        if getattr(e.response, "status_code", None) != 404:
            raise
        data = None
    if isinstance(data, list):
        data = data[0] if data else None
    if not data:
        raise LookupError(f"{source.name} holds no {survey} alert for {object_id}")
    data = {**data, "objectId": str(object_id)}
    images = None
    candid = data.get("candid") or (data.get("candidate") or {}).get("candid")
    if cutouts and candid is not None:
        try:
            images = source.broker_class.get_cutouts(source, candid, None, **kwargs)
        except Exception as e:
            log(f"No cutouts for {object_id} from {source.name}: {e}")
    return data, images


def _latest_candid(data):
    detections = [
        p
        for p in data.get("prv_candidates") or []
        if p.get("candid") is not None and p.get("jd") is not None
    ]
    if detections:
        return max(detections, key=lambda p: p["jd"])["candid"]
    return data.get("candid") or (data.get("candidate") or {}).get("candid")


CUTOUT_RETRY_DELAY = 300
CUTOUT_RETRIES = 3
_cutout_retries = set()


async def _add_cutouts_later(oid, survey):
    """Thumbnails for an object whose alert reached us before it reached BOOM."""
    from baselayer.app.models import async_plain_session_factory

    from ..models import Thumbnail
    from ._thumbnails import add_thumbnails

    for _ in range(CUTOUT_RETRIES):
        await asyncio.sleep(CUTOUT_RETRY_DELAY)
        try:
            data, cutouts = await asyncio.to_thread(_from_alerts_broker, oid, survey)
        except LookupError:
            continue
        except Exception as e:
            log(f"No cutouts for {oid}: {e}")
            return
        if not cutouts:
            return
        async with async_plain_session_factory() as session:
            if await session.scalar(
                sa.select(sa.exists().where(Thumbnail.obj_id == oid))
            ):
                return
            await add_thumbnails(
                oid,
                cutouts,
                survey,
                session,
                jd=(data.get("candidate") or {}).get("jd"),
            )
            await session.commit()
        return


def _retry_cutouts(oid, survey):
    task = asyncio.create_task(_add_cutouts_later(oid, survey))
    _cutout_retries.add(task)
    task.add_done_callback(_cutout_retries.discard)


def is_plain_stream_message(payload):
    """Whether a stream message came from the wrong one of Lasair's three streams.

    Lasair's own advice is to key on the alert being absent rather than empty:
    the selected-columns stream carries no alert at all, so its absence is
    certain, where an empty lightcurve inside one is only a quiet object. LSST
    nests it under ``alert``, ZTF under ``candidates``.
    """
    if not isinstance(payload, dict):
        return False
    return not isinstance(payload.get("alert"), dict) and not isinstance(
        payload.get("candidates"), list
    )


def _incomplete_message(payload, object_id):
    """Whether a stream message lacks the photometry or the position an object
    needs, as every message off the selected-columns stream does."""
    if is_plain_stream_message(payload):
        return True
    candidate = normalize_stream_message(payload, object_id).get("candidate") or {}
    return candidate.get("ra") is None or candidate.get("dec") is None


def normalize_stream_message(payload, object_id):
    """Standard alert shape from a stream message, whichever instance sent it."""
    return _normalize_object(payload, object_id)


async def _ingest_object(broker, oid, survey, filter_ids, payload=None, token=None):
    """Register one Lasair object as a Candidate and save any annotator
    annotations it carried. The photometry is the stream message's, or BOOM's
    when there is no message (backfill, polling) or the message lacks the
    photometry or the position, and the cutouts are BOOM's. Lasair is asked for
    the object only when BOOM does not hold it.
    """
    from baselayer.app.models import async_plain_session_factory

    from ..models import Thumbnail, User
    from ._save import save_object_as_candidate

    if payload is not None and _incomplete_message(payload, oid):
        payload = None
    async with async_plain_session_factory() as session:
        user = await session.scalar(sa.select(User).where(User.id == 1))
        has_thumbnails = await session.scalar(
            sa.select(sa.exists().where(Thumbnail.obj_id == oid))
        )
        cutouts = None
        if payload is None:
            try:
                data, cutouts = await asyncio.to_thread(
                    _from_alerts_broker, oid, survey, not has_thumbnails
                )
            except LookupError:
                obj = await asyncio.to_thread(_object, broker, oid, token)
                data = _normalize_object(obj, oid)
                if not has_thumbnails:
                    _retry_cutouts(oid, survey)
            passing_alert_id = _latest_candid(data)
        else:
            data = _normalize_object(payload, oid)
            passing_alert_id = data.get("candidate", {}).get("candid")
            if not has_thumbnails:
                try:
                    _, cutouts = await asyncio.to_thread(
                        _from_alerts_broker, oid, survey
                    )
                except LookupError:
                    _retry_cutouts(oid, survey)
                except Exception as e:
                    log(f"No cutouts for {oid}: {e}")
        await save_object_as_candidate(
            data,
            survey,
            session,
            user,
            filter_ids,
            passing_alert_id=passing_alert_id,
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
    Lasair uses across its LSST and ZTF deployments. A filter's selected columns
    keep the case its SQL gave them, so the key is matched in any case."""
    if not isinstance(payload, dict):
        return None
    keys = {str(k).lower(): v for k, v in payload.items()}
    for key in ("diaobjectid", "objectid", "object"):
        value = keys.get(key)
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
        "stream_epoch": kafka.get("stream_epoch") or 0,
    }
    sets = [shared] if (shared["topics"] or shared["topic_filter_ids"]) else []
    for entry in extra or []:
        merged = {**kafka, **(entry.get("kafka") or {})}
        sets.append(
            {
                "label": entry.get("label") or merged.get("username") or "account",
                "credential_id": entry.get("credential_id"),
                "kafka": merged,
                "token": entry.get("token"),
                "topics": entry.get("topics") or [],
                "topic_filter_ids": entry.get("topic_filter_ids") or {},
                "filter_ids": entry.get("filter_ids")
                or (altdata.get("filter_ids") or []),
                "stream_epoch": entry.get("stream_epoch") or 0,
            }
        )
    return sets


def _prepare_batch(msgs, topic_filter_ids, default_filter_ids, read_from_boom=False):
    """Split a polled batch into work to do and messages that need none.

    Returns the finished messages, the work, and any topic found to be
    streaming something we cannot ingest.

    A message that cannot be decoded or carries no objectId is finished rather
    than failed, and so is one lacking the photometry or the sky position when
    there is no BOOM to read them from: leaving it outstanding would stall its
    partition for good, and none of these gets better by being tried again.
    Where one object appears more than once, only its newest alert is ingested
    and the earlier ones are finished, which also keeps two writes for the same
    object out of the same batch.
    """
    finished = set()
    unusable = {}
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
        if not read_from_boom:
            if is_plain_stream_message(payload):
                unusable[msg.topic()] = PLAIN_STREAM_DETAIL
                finished.add(key)
                continue
            candidate = normalize_stream_message(payload, oid).get("candidate") or {}
            if candidate.get("ra") is None or candidate.get("dec") is None:
                unusable[msg.topic()] = NO_POSITION_DETAIL
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
    return finished, work, unusable


def _update_topic_status(status, work, unusable):
    """Fold a batch's outcome into the per-topic status. Returns whether it moved.

    A topic absent from the status has had nothing consumed from it yet, which
    the filter page shows differently from one known to be delivering. A topic
    is only faulted when the whole batch was unusable: one alert arriving
    without its payload is not evidence against a topic that is otherwise
    delivering.
    """
    delivering = {msg.topic() for msg, _payload, _filter_ids in work.values()}
    changed = False
    for topic in delivering | set(unusable):
        detail = None if topic in delivering else unusable[topic]
        was = status.get(topic) or {}
        if was.get("usable") == (detail is None) and was.get("detail") == detail:
            continue
        status[topic] = {
            "usable": detail is None,
            "detail": detail,
            "at": datetime.now(UTC).isoformat(),
        }
        changed = True
        log(
            f"Lasair topic {topic} cannot be ingested: {detail}"
            if detail
            else f"Lasair topic {topic} is delivering ingestable alerts"
        )
    return changed


async def _store_topic_status(credential_id, status):
    """Mirror the status onto the credential row, which is what the filter page
    reads. The broker's own shared account has no such row, so there it is
    logged and nothing more."""
    from baselayer.app.models import async_plain_session_factory

    from ..models import BrokerCredential

    try:
        async with async_plain_session_factory() as session:
            row = await session.get(BrokerCredential, credential_id)
            if row is None:
                return
            row.topic_status = dict(status)
            await session.commit()
    except Exception as e:
        log(f"Could not record Lasair topic status on credential {credential_id}: {e}")


async def _ingest_batch(broker, survey, work, concurrency, token=None):
    """Ingest a batch, at most `concurrency` at a time. Returns {key: succeeded}."""
    semaphore = asyncio.Semaphore(concurrency)

    async def run(oid, msg, payload, filter_ids):
        async with semaphore:
            try:
                await _ingest_object(
                    broker, oid, survey, filter_ids, payload=payload, token=token
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

    from ._kafka import kafka_consumer_config, replay_group_id

    kafka = credentials["kafka"]
    topic_filter_ids = {
        str(k): v for k, v in (credentials["topic_filter_ids"] or {}).items()
    }
    topics = list(dict.fromkeys(list(credentials["topics"]) + list(topic_filter_ids)))
    maxtimeout = float(kafka.get("maxtimeout", 5))

    # Suffixed per account: a shared group drives another account's offsets.
    base = kafka.get("group_id") or f"skyportal-broker-{broker.id}"
    group = f"{base}-{credentials['label']}"
    group = replay_group_id(group, credentials.get("stream_epoch"))
    config = kafka_consumer_config({**kafka, "group_id": group}, group)
    if credentials.get("stream_epoch"):
        config["auto.offset.reset"] = "earliest"
    # Auto-commit still runs, but only over offsets we store, and we store one
    # after it has been ingested: on the default a crash acknowledges whatever
    # the five-second timer had reached and those alerts are never seen again.
    config["enable.auto.offset.store"] = False
    try:
        await asyncio.to_thread(_alerts_broker, survey)
        read_from_boom = True
    except ValueError:
        read_from_boom = False
    consumer = Consumer(config)
    consumer.subscribe(topics)
    log(
        f"Lasair Kafka ingestion (broker {broker.id}, account "
        f"{credentials['label']}): subscribed to {topics}"
    )
    ingested = 0
    last_report = time.monotonic()
    # What the batches so far have shown about each topic, written through to
    # the credential row whenever it changes rather than on every batch.
    topic_status = {}
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
            finished, work, unusable = _prepare_batch(
                msgs, topic_filter_ids, credentials["filter_ids"], read_from_boom
            )
            if _update_topic_status(topic_status, work, unusable) and credentials.get(
                "credential_id"
            ):
                await _store_topic_status(credentials["credential_id"], topic_status)
            results = await _ingest_batch(
                broker, survey, work, concurrency, token=credentials["token"]
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


async def _stored_broker(broker):
    """The broker as stored now, since the caller's copy is detached and stale."""
    from baselayer.app.models import async_plain_session_factory

    from ..models import Broker

    async with async_plain_session_factory() as session:
        row = await session.scalar(sa.select(Broker).where(Broker.id == broker.id))
        if row is None:
            return broker
        session.expunge(row)
        return row


async def _run_kafka_ingestion(
    broker, survey, stop=None, max_messages=None, credentials=None
):
    """Consume Lasair's per-filter Kafka streams and register each object as a
    Candidate, one consumer per account.

    A topic carrying the lightcurve (``lite_lightcurve`` or ``full``) is ingested
    from the message itself, with the cutouts read from BOOM. A message lacking
    the lightcurve or the position is read from BOOM entirely. ``credentials``
    pins the accounts to consume; by default the stored ones, re-read every
    ``CREDENTIAL_RESCAN_INTERVAL`` so a user registering an account is picked up
    without restarting the service.
    """
    stop = stop or asyncio.Event()
    # Shared so max_messages bounds the run, not each consumer separately.
    budget = {"remaining": max_messages}
    running = {}
    stops = {}
    epochs = {}
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
            if credentials is None:
                extra = await _user_credential_sets(broker)
                current = await _stored_broker(broker)
            else:
                extra, current = credentials, broker
            sets = {c["label"]: c for c in _credential_sets(current, extra)}
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
                if (
                    label in running
                    and not running[label].done()
                    and epochs.get(label) != account["stream_epoch"]
                ):
                    stops.pop(label).set()
                    retiring.append((label, running.pop(label)))
                if label not in running or running[label].done():
                    stops[label] = asyncio.Event()
                    epochs[label] = account["stream_epoch"]
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


DEFAULT_QUERY_FIELDS = "objects.objectId, objects.ramean, objects.decmean"
BACKFILL_LIMIT = 1000


def filter_query(filter_row):
    """The Lasair SQL a skyportal Filter stores, or None when it holds none."""
    altdata = filter_row.altdata if isinstance(filter_row.altdata, dict) else {}
    lasair = altdata.get("lasair") if isinstance(altdata, dict) else None
    if not isinstance(lasair, dict) or not lasair.get("tables"):
        return None
    return {
        "fields": lasair.get("selected")
        or lasair.get("fields")
        or DEFAULT_QUERY_FIELDS,
        "tables": lasair["tables"],
        "conditions": lasair.get("conditions", ""),
    }


async def _run_backfill(
    broker,
    survey,
    filter_row,
    token=None,
    limit=BACKFILL_LIMIT,
    stop=None,
    on_progress=None,
):
    """Ingest what Lasair's own database already holds for one filter.

    The stream only reaches back as far as Lasair retains it, so a filter that
    matched something last month has nothing to replay. This runs the filter's
    saved SQL once, with the requesting user's own token, and reads each match
    from BOOM. Returns (ingested, failed, found).
    """
    query = filter_query(filter_row)
    if query is None:
        raise ValueError(
            f"Filter {filter_row.id} has no saved Lasair query to backfill from. "
            "Open it in the filter builder, save a query, then try again."
        )
    if not token:
        raise ValueError(
            "A Lasair backfill runs on your own Lasair token. Add it on the "
            "Lasair broker's page, then try again."
        )
    rows = await asyncio.to_thread(
        _query,
        broker,
        query["fields"],
        query["tables"],
        query["conditions"],
        limit,
        token,
    )
    rows = rows or []
    oids = []
    for row in rows:
        oid = row.get("diaObjectId") or row.get("objectId") or row.get("object")
        if oid is not None and str(oid) not in oids:
            oids.append(str(oid))
    log(
        f"Lasair backfill (broker {broker.id}, filter {filter_row.id}): "
        f"{len(oids)} objects to ingest"
    )
    ingested = failed = 0
    pending = list(oids)
    retried = set()
    while pending:
        if stop is not None and stop.is_set():
            break
        oid = pending.pop(0)
        try:
            await _ingest_object(broker, oid, survey, [filter_row.id], token=token)
            ingested += 1
        except Exception as e:
            log(f"Lasair backfill could not ingest {oid}: {e}")
            if oid in retried:
                failed += 1
            else:
                retried.add(oid)
                pending.append(oid)
        if on_progress is not None:
            on_progress(ingested, failed, len(oids))
    log(
        f"Lasair backfill (broker {broker.id}, filter {filter_row.id}): "
        f"{ingested} ingested, {failed} failed, {len(oids)} found"
    )
    return ingested, failed, len(oids)


class LASAIRBROKER(BrokerAPI):
    """The Lasair broker (https://lasair.lsst.ac.uk).

    Interactive access via Lasair's REST API (called directly with ``requests``,
    no client dependency). Configure a ``Broker`` with ``altdata = {"token":
    "...", "endpoint": "..."}`` (endpoint defaults to the LSST instance).
    """

    surveys = ["ZTF", "LSST"]
    filter_kind = "query"
    supports_backfill = True
    supports_replay = True
    backfill_query = staticmethod(filter_query)

    @staticmethod
    def compile_query(broker, query):
        if query.get("tree") is None:
            return query
        return {**query, **compile_tree(query["tree"], _survey(broker))}

    @staticmethod
    def found_by(broker, filter_row, obj_id):
        altdata = filter_row.altdata if isinstance(filter_row.altdata, dict) else {}
        published = (altdata.get("lasair") or {}).get("published") or {}
        return {
            "broker": "Lasair",
            "filter": published.get("name") or filter_row.name,
            "url": f"{_site(broker)}/objects/{obj_id}/",
        }

    @staticmethod
    def publish_filter(broker, name, query, token=None):
        return _publish(
            broker, re.sub(r"\W+", "_", name.lower()).strip("_"), query, token=token
        )

    @staticmethod
    def link_filter(broker, name, topic, credentials=None):
        if topic not in available_topics(broker, credentials):
            raise ValueError(
                f"{topic} is not streaming yet. Save the filter on Lasair with "
                "a kafka stream output first."
            )
        return {"name": name, "topic": topic, "url": f"{_site(broker)}/filters/"}

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
                            "needs no credentials."
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
                "description": "From your Lasair profile.",
            },
            "username": {
                "type": "string",
                "title": "SASL username",
                "description": "Only for a private stream.",
            },
            "password": {
                "type": "string",
                "title": "SASL password",
                "description": "Only for a private stream.",
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
            return [LASAIRBROKER.get_alert(broker, object_id, session)]
        if kwargs.get("ra") is not None and kwargs.get("dec") is not None:
            return _cone(
                broker,
                float(kwargs["ra"]),
                float(kwargs["dec"]),
                radius=float(kwargs.get("radius", 5)),
                request_type=kwargs.get("requestType", "all"),
                token=kwargs.get("token"),
            )
        if kwargs.get("selected") and kwargs.get("tables"):
            return _query(
                broker,
                kwargs["selected"],
                kwargs["tables"],
                kwargs.get("conditions", ""),
                limit=int(kwargs.get("limit", 1000)),
                token=kwargs.get("token"),
            )
        raise ValueError(
            "Provide objectId, or ra+dec (cone), or selected+tables (query)."
        )

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        return _from_alerts_broker(alert_id, _survey(broker), cutouts=False)[0]

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        return _cone(
            broker,
            float(ra),
            float(dec),
            radius=float(radius),
            request_type=kwargs.get("requestType", "all"),
            token=kwargs.get("token"),
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
        tree = kwargs.get("tree") or kwargs.get("filters")
        compiled = compile_tree(tree, survey) if tree is not None else {}
        selected = (
            kwargs.get("selected")
            or compiled.get("selected")
            or _DEFAULT_SELECTED.get(survey, _DEFAULT_SELECTED["LSST"])
        )
        tables = kwargs.get("tables") or compiled.get("tables") or "objects"
        conditions = compiled.get("conditions", kwargs.get("conditions") or "")
        limit = int(kwargs.get("limit", 50))
        return _query(
            broker, selected, tables, conditions, limit=limit, token=kwargs.get("token")
        )

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        # Lasair rows carry no candid, so alert_id is an objectId.
        return _from_alerts_broker(alert_id, _survey(broker))[1]

    @staticmethod
    async def run_backfill(broker, filter_row, token=None, stop=None, **kwargs):
        """Ingest Lasair's stored matches for one filter, once.

        Independent of the stream: it neither reads nor moves a consumer offset,
        so it can run while ingestion is consuming, or with ingestion off
        entirely.
        """
        return await _run_backfill(
            broker,
            _survey(broker),
            filter_row,
            token=token,
            limit=int(kwargs.get("limit") or BACKFILL_LIMIT),
            stop=stop,
            on_progress=kwargs.get("on_progress"),
        )

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
                query = filter_query(f)
                if query is None:
                    continue
                queries.append({**query, "name": f.name, "filter_ids": [f.id]})
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
                selected = query.get("fields") or DEFAULT_QUERY_FIELDS
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
