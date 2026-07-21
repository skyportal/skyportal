from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/ampel")

# AMPEL publishes LSST transient reports on SCIMMA Hopskotch (Kafka, SASL_SSL).
DEFAULT_SERVERS = "kafka.scimma.org:9092"
DEFAULT_TOPICS = [
    "ampel.lsst.extragalactic-transients",
    "ampel.lsst.extragalactic-infants",
]


def _normalize_band(band):
    # AMPEL bands are full LSST filter names ("lssti"); the shared save re-prefixes
    # with the survey, so return just the passband letter.
    if band and band.lower().startswith("lsst"):
        return band[4:]
    return band


def _normalize_ampel_report(report):
    """Reshape an AMPEL LSST transient report ({object, photometry[], ...}, with
    photometry in flux space: time=JD, flux in nJy) into the standard shape.
    Returns (data, passing_alert_id)."""
    obj = report.get("object") or {}
    object_id = obj.get("external_id") or obj.get("id")
    if object_id is None:
        return None, None
    prv = []
    for p in report.get("photometry") or []:
        if p.get("fluxerr") is None:
            continue
        prv.append(
            {
                "jd": p.get("time"),  # already a Julian Date
                "psfFlux": p.get("flux"),  # nJy; shared save scales to Jy
                "psfFluxErr": p.get("fluxerr"),
                "band": _normalize_band(p.get("band")),
                "ra": obj.get("ra"),
                "dec": obj.get("dec"),
            }
        )
    data = {
        "objectId": str(object_id),
        "candidate": {"ra": obj.get("ra"), "dec": obj.get("dec")},
        "prv_candidates": prv,
    }
    return data, obj.get("id")


class AMPELBROKER(BrokerAPI):
    """The AMPEL broker (DESY/HU-Berlin), LSST transient reports.

    Ingestion-only: consumes AMPEL's public LSST transient-report topics from
    SCIMMA Hopskotch (Kafka, SASL_SSL/SCRAM — needs a free SCIMMA account).
    Each report carries the object + its Rubin photometry (flux space) + AMPEL
    classifications. Configure a ``Broker`` with ``altdata['scimma']``
    (username/password, optional servers/group_id/topics) + ``filter_ids``.
    """

    surveys = ["LSST"]
    filter_kind = "tags"  # the Hopskotch topics are the science-tag menu

    form_json_schema_config = {
        "type": "object",
        "required": ["scimma"],
        "properties": {
            "scimma": {
                "type": "object",
                "title": "SCIMMA Hopskotch",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "servers": {"type": "string", "default": DEFAULT_SERVERS},
                    "group_id": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                },
            },
            "survey": {"type": "string", "enum": ["LSST"], "default": "LSST"},
        },
    }

    ui_json_schema = {"scimma": {"password": {"ui:widget": "password"}}}

    @staticmethod
    def validate_config(altdata):
        scimma = (altdata or {}).get("scimma") or {}
        if not (scimma.get("username") and scimma.get("password")):
            raise ValueError("Broker altdata must include scimma.username/password.")

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Consume AMPEL's Hopskotch topics (self-describing Avro reports) and
        register each as a Candidate under ``filter_ids``."""
        import asyncio
        import io

        import fastavro
        import sqlalchemy as sa
        from confluent_kafka import Consumer, KafkaError

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        scimma = altdata.get("scimma") or {}
        survey = altdata.get("survey", "LSST")
        filter_ids = altdata.get("filter_ids") or []
        topics = scimma.get("topics") or DEFAULT_TOPICS

        config = {
            "bootstrap.servers": scimma.get("servers", DEFAULT_SERVERS),
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.username": scimma["username"],
            "sasl.password": scimma["password"],
            "group.id": scimma.get("group_id", f"{scimma['username']}-skyportal"),
            "auto.offset.reset": scimma.get("auto_offset_reset", "earliest"),
        }
        consumer = Consumer(config)
        consumer.subscribe(topics)
        log(f"AMPEL ingestion (broker {broker.id}): subscribed to {topics}")

        count = 0
        try:
            while not (stop is not None and stop.is_set()):
                msg = await asyncio.to_thread(consumer.poll, 2.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        log(f"Kafka error: {msg.error()}")
                    continue
                report = None
                for rec in fastavro.reader(io.BytesIO(msg.value())):
                    report = rec
                    break
                if report is None:
                    continue
                data, candid = _normalize_ampel_report(report)
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
                            filter_ids,
                            passing_alert_id=candid,
                        )
                except Exception as e:
                    log(f"Error ingesting AMPEL report {data.get('objectId')}: {e}")
                count += 1
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            consumer.close()
        log(f"AMPEL ingestion (broker {broker.id}): consumed {count} reports")
        return count
