"""JPL Scout NEO ToO candidate ingestion service.

Consumes the Kafka stream published by lsst-sssc/scout-alert-bridge, which polls
the JPL Scout NEOCP assessment and applies the SSSC NEOs WG "Filter Criteria for
NEO Rubin ToO Triggers" (v0.2). Each message is a candidate state change, not an
alert: there is no photometry, instrument or cutout, so this does not go through
the broker ingestion path.
"""

import json
import time
import traceback
import uuid

from confluent_kafka import Consumer

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db, session_context_id
from baselayer.log import make_log
from skyportal.utils.scout_ingest import ScoutIngestError, ingest_scout_event
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("scout_service")

scout_cfg = cfg.get("scout", {})

topic = scout_cfg.get("topic")
kafka_server = scout_cfg.get("kafka_server")
username = scout_cfg.get("scimma_username")
password = scout_cfg.get("scimma_password")
group_ids = scout_cfg.get("group_ids") or []
bot_user_id = scout_cfg.get("bot_user_id")
allow_relaxed = scout_cfg.get("allow_relaxed_test", False)
from_start = scout_cfg.get("from_start", False)


def is_configured():
    required = {
        "scout.topic": topic,
        "scout.kafka_server": kafka_server,
        "scout.bot_user_id": bot_user_id,
        "scout.group_ids": group_ids,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        log(f"Not polling JPL Scout events, missing config: {', '.join(missing)}")
        return False
    return True


def build_consumer():
    group_id = f"skyportal-scout-{topic}"
    if from_start:
        group_id += f"-{int(time.time())}"

    conf = {
        "bootstrap.servers": kafka_server,
        "group.id": group_id,
        "auto.offset.reset": "earliest" if from_start else "latest",
        "enable.auto.commit": True,
    }
    # Hopskotch requires SASL; a local broker used for testing does not.
    if username and password:
        conf.update(
            {
                "security.protocol": "SASL_SSL",
                "sasl.mechanisms": "SCRAM-SHA-512",
                "sasl.username": username,
                "sasl.password": password,
            }
        )
    return Consumer(conf)


def handle_message(payload):
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        log(f"Failed to parse scout message: {e}")
        return

    session_context_id.set(uuid.uuid4().hex)
    with DBSession() as session:
        try:
            result = ingest_scout_event(
                session,
                event,
                group_ids,
                bot_user_id,
                allow_relaxed=allow_relaxed,
            )
            session.commit()
            log(f"{result['obj_id']}: {result['action']}")
        except ScoutIngestError as e:
            session.rollback()
            log(f"Rejected scout message: {e}")
        except Exception as e:
            session.rollback()
            log(f"Error ingesting scout message: {e}")
            traceback.print_exc()


@check_loaded(logger=log)
def poll_events(*args, **kwargs):
    try:
        consumer = build_consumer()
        consumer.subscribe([topic])
    except Exception as e:
        log(f"Failed to subscribe to scout topic {topic}: {e}")
        return

    log(f"Polling JPL Scout events on {topic}")
    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                log(f"Kafka error: {message.error()}")
                continue
            handle_message(message.value())
    finally:
        consumer.close()


if __name__ == "__main__":
    if is_configured():
        try:
            poll_events()
        except Exception as e:
            log(f"Error polling scout events: {e}")

    # Idle rather than exit so supervisor doesn't restart-loop.
    while True:
        time.sleep(3600)
