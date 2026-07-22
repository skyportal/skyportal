import requests

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/babamul")

DEFAULT_BASE_URL = "https://babamul.caltech.edu/api/babamul"
DEFAULT_SURVEY = "ZTF"
DEFAULT_TIMEOUT = 30  # seconds


def _request(broker, path, params=None):
    """GET against the babamul REST API using ``broker.altdata`` (``token``,
    optional ``base_url``). Returns the parsed ``data`` payload."""
    altdata = broker.altdata or {}
    token = altdata.get("token")
    if not token:
        raise ValueError("Broker altdata is missing 'token'.")
    base_url = altdata.get("base_url", DEFAULT_BASE_URL)
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    response = requests.get(
        url,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _survey(broker, kwargs):
    return kwargs.get("survey") or (broker.altdata or {}).get("survey", DEFAULT_SURVEY)


class BABAMULBROKER(BrokerAPI):
    """The babamul broker (BOOM ecosystem, ZTF/LSST alerts).

    Interactive access to babamul's REST API. Configure a ``Broker`` with
    ``altdata = {"token": "...", "survey": "ZTF", "base_url": "..."}`` (base_url
    defaults to the production instance).
    """

    surveys = ["ZTF", "LSST"]

    form_json_schema_config = {
        "type": "object",
        "required": ["token"],
        "properties": {
            "token": {"type": "string", "title": "babamul API token"},
            "survey": {
                "type": "string",
                "title": "Survey",
                "enum": ["ZTF", "LSST"],
                "default": DEFAULT_SURVEY,
            },
            "base_url": {
                "type": "string",
                "title": "API base URL",
                "default": DEFAULT_BASE_URL,
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
        survey = _survey(broker, kwargs)
        params = {}
        if kwargs.get("objectId"):
            params["object_id"] = kwargs["objectId"]
        if kwargs.get("ra") is not None and kwargs.get("dec") is not None:
            params["ra"] = kwargs["ra"]
            params["dec"] = kwargs["dec"]
            params["radius_arcsec"] = kwargs.get("radius", 5)
        return _request(broker, f"surveys/{survey}/alerts", params=params)

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        survey = _survey(broker, kwargs)
        return _request(broker, f"surveys/{survey}/objects/{alert_id}")

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        # cutouts are keyed by candid; ``alert_id`` is the candid here. Pass the
        # base64-encoded FITS cutouts through unchanged for the frontend to render.
        survey = _survey(broker, kwargs)
        return _request(
            broker, f"surveys/{survey}/cutouts", params={"candid": alert_id}
        )

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Consume babamul's Kafka stream (Avro ZTF alerts) and ingest each alert
        via the shared transform, registering Candidates under ``filter_ids``.
        Config lives in ``broker.altdata["kafka"]`` (host/port/group_id/username/
        password/sasl_mechanism/topics) plus ``filter_ids`` (skyportal Filter ids
        the alerts pass) and ``survey``.
        """
        import asyncio

        import sqlalchemy as sa
        from confluent_kafka import Consumer, KafkaError

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._kafka import kafka_consumer_config, read_avro
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        kafka = altdata.get("kafka") or {}
        survey = altdata.get("survey", DEFAULT_SURVEY)
        filter_ids = altdata.get("filter_ids") or []

        consumer = Consumer(
            kafka_consumer_config(kafka, f"skyportal-broker-{broker.id}")
        )
        topics = kafka.get("topics") or []
        consumer.subscribe(topics)
        log(f"babamul ingestion (broker {broker.id}): subscribed to {topics}")

        count = 0
        try:
            while not (stop is not None and stop.is_set()):
                # poll is blocking; offload so one event loop can host several brokers.
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
                candid = record.get("candid") or (record.get("candidate") or {}).get(
                    "candid"
                )
                try:
                    async with async_plain_session_factory() as session:
                        user = await session.scalar(sa.select(User).where(User.id == 1))
                        await save_object_as_candidate(
                            record,
                            survey,
                            session,
                            user,
                            filter_ids,
                            passing_alert_id=candid,
                        )
                except Exception as e:
                    log(f"Error ingesting alert {record.get('objectId')}: {e}")
                count += 1
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            consumer.close()
        log(f"babamul ingestion (broker {broker.id}): consumed {count} alerts")
        return count
