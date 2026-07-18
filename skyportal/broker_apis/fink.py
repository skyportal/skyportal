import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/fink")

# Fink ZTF alerts use fid (1/2/3); LSST alerts carry a string band already.
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}

# Fink's public (no-auth) Science Portal REST API, used for interactive queries
# (the Kafka livestream, used for ingestion, is separate and credentialed).
# Fink's REST hosts carry the survey in the subdomain (ztf/lsst).
FINK_REST_URL = {
    "ZTF": "https://api.ztf.fink-portal.org",
    "LSST": "https://api.lsst.fink-portal.org",
}
FINK_TIMEOUT = 60  # seconds


def _decode_fink_message(msg):
    """Fink's Kafka messages are self-describing: the message key is the Avro
    schema (JSON) and the value is a schemaless Avro record, so decoding needs
    only fastavro — no schema registry and no fink-client. Returns None if the
    key (schema) is missing."""
    import io
    import json

    import fastavro

    key = msg.key()
    if key is None:
        return None
    schema = fastavro.parse_schema(json.loads(key))
    return fastavro.schemaless_reader(io.BytesIO(msg.value()), schema)


def _fink_survey(broker, kwargs=None):
    return (
        (kwargs or {}).get("survey") or (broker.altdata or {}).get("survey", "ZTF")
    ).upper()


def _fink_base(broker, kwargs=None):
    altdata = broker.altdata or {}
    return altdata.get("rest_url") or FINK_REST_URL.get(
        _fink_survey(broker, kwargs), FINK_REST_URL["ZTF"]
    )


def _fink_post(broker, path, payload, kwargs=None):
    """POST to the Fink REST API and return the list of records."""
    url = f"{_fink_base(broker, kwargs).rstrip('/')}/{path.lstrip('/')}"
    response = requests.post(url, json=payload, timeout=FINK_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    return data.get("data", []) if isinstance(data, dict) else []


def _normalize_fink_object(object_id, rows):
    """Reshape Fink ``/api/v1/objects`` rows (prefixed ``i:*`` columns, one per
    epoch) into the standard {objectId, candidate, prv_candidates} shape."""
    detections = [r for r in rows if r.get("i:magpsf") is not None]
    detections.sort(key=lambda r: r.get("i:jd") or 0)
    latest = detections[-1] if detections else (rows[-1] if rows else {})
    prv = [
        {
            "jd": r.get("i:jd"),
            "magpsf": r.get("i:magpsf"),
            "sigmapsf": r.get("i:sigmapsf"),
            "band": _FID_TO_BAND.get(r.get("i:fid")),
            "ra": r.get("i:ra"),
            "dec": r.get("i:dec"),
        }
        for r in detections
    ]
    return {
        "objectId": object_id,
        "candidate": {
            "ra": latest.get("i:ra"),
            "dec": latest.get("i:dec"),
            "magpsf": latest.get("i:magpsf"),
            "jd": latest.get("i:jd"),
            "band": _FID_TO_BAND.get(latest.get("i:fid")),
        },
        "prv_candidates": prv,
    }


def _normalize_fink_lsst(object_id, rows):
    """Reshape Fink LSST ``/api/v1/sources`` rows (prefixed ``r:*`` columns, flux
    space: psfFlux in nJy, string band) into the standard shape. The shared save
    scales psfFlux to Jy and applies the LSST zeropoint."""
    prv = []
    for r in rows:
        mjd = r.get("r:midpointMjdTai")
        prv.append(
            {
                "jd": (mjd + 2400000.5) if mjd is not None else None,
                "psfFlux": r.get("r:psfFlux"),
                "psfFluxErr": r.get("r:psfFluxErr"),
                "band": r.get("r:band"),
                "ra": r.get("r:ra"),
                "dec": r.get("r:dec"),
            }
        )
    prv = [p for p in prv if p["psfFluxErr"] is not None]
    prv.sort(key=lambda d: d["jd"] or 0)
    latest = prv[-1] if prv else {}
    return {
        "objectId": str(object_id),
        "candidate": {
            "ra": latest.get("ra"),
            "dec": latest.get("dec"),
            "jd": latest.get("jd"),
            "band": latest.get("band"),
        },
        "prv_candidates": prv,
    }


class FINKBROKER(BrokerAPI):
    """The Fink alert broker.

    Two independent surfaces: interactive queries against Fink's public (no-auth)
    Science Portal REST API (object lookup / cone search, hence get_alert /
    query_alerts / cone_search / the base save_as_source), and ingestion from the
    credentialed ``fink-client`` Kafka livestream (run_ingestion). Configure a
    ``Broker`` with ``altdata`` holding a ``fink`` block (Kafka
    servers/username/password/group_id/topics) for ingestion, ``survey``
    ("ZTF"/"LSST"), ``filter_ids`` (Filters the science-topic alerts pass), and
    optionally ``rest_url`` to override the REST endpoint. Fink 'topics' are
    science tags (e.g. ``fink_kn_candidates_ztf``).
    """

    surveys = ["ZTF", "LSST"]

    form_json_schema_config = {
        "type": "object",
        "required": ["fink"],
        "properties": {
            "fink": {
                "type": "object",
                "title": "Fink Kafka",
                "properties": {
                    "servers": {"type": "string", "title": "Bootstrap servers"},
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "group_id": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "topic_filter_ids": {
                        "type": "object",
                        "title": "Per-topic Filter ids",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                },
            },
            "survey": {
                "type": "string",
                "title": "Survey",
                "enum": ["ZTF", "LSST"],
                "default": "ZTF",
            },
        },
    }

    ui_json_schema = {"fink": {"password": {"ui:widget": "password"}}}

    @staticmethod
    def validate_config(altdata):
        # Interactive REST is public; the Kafka ingestion config (fink.servers) is
        # only needed for run_ingestion, which validates it there. Nothing is
        # required at config time, so a Fink broker can be created config-free.
        return

    # ------------------------------------------------------------------ #
    # Interactive queries via Fink's public REST API (no credentials).   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        survey = _fink_survey(broker, kwargs)
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return [FINKBROKER.get_alert(broker, object_id, session, **kwargs)]
        ra, dec = kwargs.get("ra"), kwargs.get("dec")
        if ra is not None and dec is not None:
            rows = _fink_post(
                broker,
                "api/v1/conesearch",
                {
                    "ra": str(ra),
                    "dec": str(dec),
                    "radius": str(kwargs.get("radius", 5)),
                },
                kwargs,
            )
            oid_key = "r:diaObjectId" if survey == "LSST" else "i:objectId"
            normalize = (
                _normalize_fink_lsst if survey == "LSST" else _normalize_fink_object
            )
            by_obj: dict = {}
            for r in rows or []:
                oid = r.get(oid_key)
                if oid:
                    by_obj.setdefault(oid, []).append(r)
            return [normalize(oid, rs) for oid, rs in by_obj.items()]
        raise ValueError("Provide objectId, or ra+dec.")

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        if _fink_survey(broker, kwargs) == "LSST":
            rows = _fink_post(
                broker,
                "api/v1/sources",
                {"diaObjectId": alert_id, "output-format": "json"},
                kwargs,
            )
            return _normalize_fink_lsst(alert_id, rows or [])
        rows = _fink_post(
            broker,
            "api/v1/objects",
            {"objectId": alert_id, "output-format": "json"},
            kwargs,
        )
        object_id = rows[0].get("i:objectId", alert_id) if rows else alert_id
        return _normalize_fink_object(object_id, rows or [])

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        return _fink_post(
            broker,
            "api/v1/conesearch",
            {"ra": str(ra), "dec": str(dec), "radius": str(radius)},
            kwargs,
        )

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        """Fetch science/template/difference stamps for an object. Fink returns
        rendered PNGs, so return them as data: URLs (the frontend uses them
        directly rather than decoding FITS). ``alert_id`` is the objectId."""
        import base64

        base = _fink_base(broker, kwargs).rstrip("/")
        out = {}
        for kind, field in (
            ("Science", "cutoutScience"),
            ("Template", "cutoutTemplate"),
            ("Difference", "cutoutDifference"),
        ):
            try:
                response = requests.post(
                    f"{base}/api/v1/cutouts",
                    json={"objectId": alert_id, "kind": kind},
                    timeout=FINK_TIMEOUT,
                )
                response.raise_for_status()
                encoded = base64.b64encode(response.content).decode("utf-8")
                out[field] = f"data:image/png;base64,{encoded}"
            except Exception as e:
                log(f"Fink cutout {kind} failed for {alert_id}: {e}")
        return out

    @staticmethod
    def _normalize(survey, alert):
        """Reshape a Fink alert (survey-specific) into the standard alert shape
        (``objectId`` + ``candidate`` + a single-detection ``prv_candidates``).
        Returns ``(data, passing_alert_id)`` or ``(None, None)``."""
        if survey == "LSST":
            src = alert.get("diaSource") or {}
            obj = alert.get("diaObject") or {}
            oid = obj.get("diaObjectId")
            if oid is None:
                return None, None
            mjd = src.get("midpointMjdTai")
            prv = [
                {
                    "jd": (mjd + 2400000.5) if mjd is not None else None,
                    "band": src.get("band"),
                    "psfFlux": src.get("psfFlux"),  # nJy; shared save scales to Jy
                    "psfFluxErr": src.get("psfFluxErr"),
                    "ra": src.get("ra"),
                    "dec": src.get("dec"),
                }
            ]
            data = {
                "objectId": str(oid),
                "candidate": {
                    "ra": obj.get("ra") or src.get("ra"),
                    "dec": obj.get("dec") or src.get("dec"),
                },
                "prv_candidates": prv,
            }
            return data, src.get("diaSourceId")

        cand = alert.get("candidate") or {}
        oid = alert.get("objectId")
        if oid is None:
            return None, None
        prv = [
            {
                "jd": cand.get("jd"),
                "band": _FID_TO_BAND.get(cand.get("fid")),
                "magpsf": cand.get("magpsf"),
                "sigmapsf": cand.get("sigmapsf"),
                "ra": cand.get("ra"),
                "dec": cand.get("dec"),
            }
        ]
        data = {
            "objectId": oid,
            "candidate": {
                "ra": cand.get("ra"),
                "dec": cand.get("dec"),
                "magpsf": cand.get("magpsf"),
            },
            "prv_candidates": prv,
        }
        return data, cand.get("candid")

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Consume Fink's science-topic Kafka livestream and register each alert
        as a Candidate. Uses confluent_kafka + fastavro directly (Fink ships the
        Avro schema in each message key), so no fink-client is needed. Config in
        ``broker.altdata['fink']``: ``servers`` (Kafka bootstrap, required),
        ``topics``, ``group_id``, ``username`` + ``password`` (enable SASL SCRAM),
        ``maxtimeout``, and optionally ``topic_filter_ids`` -- a ``{topic:
        [filter_id, ...]}`` map routing each topic to its own SkyPortal Filters
        (Fink topics are the science filters). Alerts from an unmapped topic fall
        back to the broker-wide ``altdata['filter_ids']``."""
        import asyncio

        import sqlalchemy as sa
        from confluent_kafka import Consumer

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        fink = altdata.get("fink") or {}
        survey = altdata.get("survey", "ZTF")
        filter_ids = altdata.get("filter_ids") or []
        # Optional per-topic routing: {topic: [filter_id, ...]}. Alerts from a
        # mapped topic become Candidates under those Filters; unmapped topics fall
        # back to the broker-wide filter_ids.
        topic_filter_ids = fink.get("topic_filter_ids") or {}
        maxtimeout = float(fink.get("maxtimeout", 5))
        # Subscribe to the explicit topics plus any keyed in the routing map.
        topics = list(
            dict.fromkeys((fink.get("topics") or []) + list(topic_filter_ids))
        )

        servers = fink.get("servers")
        if not servers:
            raise ValueError(
                "Fink ingestion requires altdata['fink']['servers'] "
                "(Kafka bootstrap servers)."
            )
        config = {
            "bootstrap.servers": servers,
            "group.id": fink.get("group_id", f"skyportal-broker-{broker.id}"),
            "auto.offset.reset": fink.get("auto_offset_reset", "earliest"),
        }
        # Fink's public livestream is passwordless (fink-client sends no SASL when
        # `password` is null); only enable SASL SCRAM when a password is actually
        # configured, else an empty password fails the auth handshake.
        if fink.get("username") and fink.get("password"):
            config.update(
                {
                    "security.protocol": "sasl_plaintext",
                    "sasl.mechanism": fink.get("sasl_mechanism", "SCRAM-SHA-512"),
                    "sasl.username": fink["username"],
                    "sasl.password": fink["password"],
                }
            )

        consumer = Consumer(config)
        consumer.subscribe(topics)
        log(f"Fink ingestion (broker {broker.id}): subscribed to {topics}")

        count = 0
        try:
            while not (stop is not None and stop.is_set()):
                msg = await asyncio.to_thread(consumer.poll, maxtimeout)
                if msg is None or msg.error():
                    continue
                # Route by the topic the alert arrived on (Fink topics are the
                # science filters); unmapped topics use the broker-wide filter_ids.
                alert_filter_ids = topic_filter_ids.get(msg.topic(), filter_ids)
                try:
                    alert = _decode_fink_message(msg)
                except Exception as e:
                    log(f"Error decoding Fink message: {e}")
                    continue
                if alert is None:
                    continue
                data, candid = FINKBROKER._normalize(survey, alert)
                if data is None:
                    continue
                try:
                    async with async_plain_session_factory() as session:
                        user = await session.scalar(sa.select(User).where(User.id == 1))
                        await save_object_as_candidate(
                            data,
                            survey,
                            session,
                            user,
                            alert_filter_ids,
                            passing_alert_id=candid,
                        )
                except Exception as e:
                    log(f"Error ingesting Fink alert {data.get('objectId')}: {e}")
                count += 1
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            consumer.close()
        log(f"Fink ingestion (broker {broker.id}): consumed {count} alerts")
        return count
