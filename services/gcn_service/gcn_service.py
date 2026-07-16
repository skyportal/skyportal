import asyncio
import json
import os
import traceback
import uuid

import lxml
import sqlalchemy as sa
import xmlschema
from gcn_kafka import Consumer

from baselayer.app import models
from baselayer.app.env import load_env
from baselayer.app.models import init_db
from skyportal.handlers.api.gcn import (
    get_json_tags,
    get_tags,
    post_gcnevent_from_json,
    post_gcnevent_from_xml,
    post_skymap_from_notice,
)
from skyportal.log import make_log
from skyportal.models import GcnEvent, User
from skyportal.utils.gcn import (
    from_igwn_gwalert,
    get_dateobs,
    get_skymap_metadata,
    get_trigger,
)
from skyportal.utils.notifications import post_notification
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

client_id = cfg["gcn.client_id"]
client_secret = cfg["gcn.client_secret"]
voevent_notice_types = cfg.get("gcn.notice_types.voevent", [])
json_notice_types = cfg.get("gcn.notice_types.json", [])

reject_tags = cfg.get("gcn.reject_tags", [])

log = make_log("gcnserver")

user_id = 1


def get_root_from_payload(payload):
    schema = (
        f"{os.path.dirname(__file__)}/../../skyportal/utils/schema/VOEvent-v2.0.xsd"
    )
    voevent_schema = xmlschema.XMLSchema(schema)
    if voevent_schema.is_valid(payload):
        # check if is string
        try:
            payload = payload.encode("ascii")
        except AttributeError:
            pass
        root = lxml.etree.fromstring(payload)
    else:
        raise ValueError("xml file is not valid VOEvent")
    return root


def is_configured():
    if client_id is None or client_id == "":
        log.info("No client_id configured to poll gcn events (config: gcn.client_id")
        return False
    if client_secret is None or client_secret == "":
        log.info(
            "No client_secret configured to poll gcn events (config: gcn.client_secret"
        )
        return False
    if (
        voevent_notice_types is None
        or voevent_notice_types == ""
        or voevent_notice_types == []
    ) and (
        json_notice_types is None or json_notice_types == "" or json_notice_types == []
    ):
        log.info(
            "No notice_types configured to poll gcn events (config: gcn.notice_types and/or gcn.json_notice_types)"
        )
        return False
    return True


@check_loaded(logger=log)
def poll_events(*args, **kwargs):
    client_group_id = cfg.get("gcn.client_group_id")
    if client_group_id is None or client_group_id == "":
        client_group_id = str(uuid.uuid4())

    config = {
        "group.id": client_group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
    try:
        consumer = Consumer(
            config=config,
            client_id=client_id,
            client_secret=client_secret,
            domain=cfg["gcn.server"],
        )
    except Exception as e:
        log.error(f"Failed to initiate consumer to poll gcn events: {e}")
        return
    try:
        consumer.subscribe(voevent_notice_types + json_notice_types)
    except Exception as e:
        log.error(f"Failed to subscribe to gcn events: {e}")
        return
    while True:
        try:
            for message in consumer.consume():
                payload = message.value()
                topic = message.topic()
                consumer.commit(message)

                if payload is None:
                    continue

                if payload.find(b"Broker: Unknown topic or partition") != -1:
                    continue

                # initialize some variables tht will be used later
                notice_type = (
                    str(topic)
                    .replace("gcn.notices.", "")
                    .replace("gcn.classic.voevent.", "")
                )
                root, tags, alert_type, dateobs, notice_id = (
                    None,
                    None,
                    None,
                    None,
                    None,
                )

                if any(topic in notice_type for notice_type in voevent_notice_types):
                    alert_type = "voevent"
                    root = get_root_from_payload(payload)
                    tags = get_tags(root, notice_type)
                    # if the notice_type is svom.voevent.grm but there is no ra/dec/error radius
                    # or if the error radius is negative, we reject the event
                    if notice_type == "svom.voevent.grm":
                        loc = root.find(
                            "./WhereWhen/ObsDataLocation/ObservationLocation"
                        )
                        if loc is None:
                            log.info(
                                f"Rejecting gcn_event from {topic} due to missing location"
                            )
                            continue
                        error = loc.find("./AstroCoords/Position2D/Error2Radius")
                        if error is None:
                            log.info(
                                f"Rejecting gcn_event from {topic} due to missing error"
                            )
                            continue
                        try:
                            error = float(error.text)
                            if error < 0:
                                raise ValueError("error is negative")
                        except ValueError:
                            log.info(
                                f"Rejecting gcn_event from {topic} due to invalid error: {error}"
                            )
                            continue

                elif any(topic in notice_type for notice_type in json_notice_types):
                    alert_type = "json"
                    payload = json.loads(payload.decode("utf8"))
                    if "igwn.gwalert" in notice_type:
                        # LVK JSON alert (GCN Classic LVC VOEvents ceased in 2026):
                        # normalize to the canonical JSON-notice shape.
                        payload = from_igwn_gwalert(payload)
                        notice_type = payload["notice_type"]
                    else:
                        payload["notice_type"] = notice_type
                    tags = get_json_tags(payload)

                    if payload["notice_type"] == "icecube.lvk_nu_track_search":
                        # 2 sigma
                        pval_bayesian = payload.get("pval_bayesian", 1)
                        if (
                            not isinstance(pval_bayesian, int | float)
                            or pval_bayesian > 0.05
                        ):
                            log.info(
                                f"Rejecting gcn_event from {topic} due to pval_bayesian: {pval_bayesian}"
                            )
                            continue

                tags_intersection = list(set(tags).intersection(set(reject_tags)))
                if len(tags_intersection) > 0:
                    log.info(
                        f"Rejecting gcn_event from {topic} due to tag(s): {tags_intersection}"
                    )
                    continue

                async def _ingest():
                    dateobs, notice_id = None, None
                    async with models.async_plain_session_factory() as session:
                        # check if the user exists in the DB, assign to session
                        user = await session.scalar(
                            sa.select(User).where(User.id == user_id)
                        )
                        if user is None:
                            log.info(
                                f"User {user_id} not found in DB, cannot ingest gcn_event"
                            )
                            return
                        session.user_or_token = user

                        # skip ingesting a retraction if the event does not exist
                        # (VOEvent path; JSON retractions are resolved by alias in
                        # post_gcnevent_from_json).
                        if alert_type == "voevent" and notice_type == "LVC_RETRACTION":
                            dateobs = get_dateobs(root)
                            trigger_id = get_trigger(root)
                            existing_event = None
                            if trigger_id is not None:
                                existing_event = await session.scalar(
                                    sa.select(GcnEvent).where(
                                        GcnEvent.trigger_id == trigger_id
                                    )
                                )
                            if existing_event is None and dateobs is not None:
                                existing_event = await session.scalar(
                                    sa.select(GcnEvent).where(
                                        GcnEvent.dateobs == dateobs
                                    )
                                )
                            if existing_event is None:
                                log.info(
                                    f"No event found to retract for gcn_event from {message.topic()}, skipping"
                                )
                                return

                        # event ingestion
                        log.info(f"Ingesting gcn_event from {message.topic()}")
                        try:
                            if alert_type == "voevent":
                                (
                                    dateobs,
                                    _,
                                    notice_id,
                                ) = await post_gcnevent_from_xml(
                                    payload,
                                    user_id,
                                    session,
                                    notice_type=notice_type,
                                    post_skymap=False,
                                    asynchronous=False,
                                    notify=False,
                                )
                            elif alert_type == "json":
                                (
                                    dateobs,
                                    _,
                                    notice_id,
                                ) = await post_gcnevent_from_json(
                                    payload,
                                    user_id,
                                    session,
                                    post_skymap=False,
                                    asynchronous=False,
                                    notify=False,
                                )
                        except Exception as e:
                            traceback.print_exc()
                            log.error(
                                f"Failed to ingest gcn_event from {message.topic()}: {e}"
                            )
                            return

                        notified_on_skymap = False
                        status, metadata = None, None
                        if alert_type == "voevent":
                            status, metadata = get_skymap_metadata(
                                root, notice_type, 15
                            )
                        elif alert_type == "json":
                            status, metadata = get_skymap_metadata(
                                payload, notice_type, 15
                            )

                        if status in ["available", "cone", "healpix_file"]:
                            log.info(
                                f"Ingesting skymap for gcn_event: {dateobs}, notice_id: {notice_id}"
                            )
                            try:
                                localization_id = await post_skymap_from_notice(
                                    dateobs,
                                    notice_id,
                                    user_id,
                                    session,
                                    asynchronous=False,
                                    notify=False,
                                )
                                request_body = {
                                    "target_class_name": "Localization",
                                    "target_id": localization_id,
                                }
                                notified_on_skymap = post_notification(
                                    request_body, timeout=30
                                )
                            except Exception as e:
                                log.error(
                                    f"Failed to ingest skymap for gcn_event: {dateobs}, notice_id: {notice_id}: {e}"
                                )
                        elif status == "unavailable":
                            log.info(
                                f"No skymap available for gcn_event: {dateobs}, notice_id: {notice_id} with url: {metadata.get('url', None)}"
                            )
                        else:
                            log.info(
                                f"No skymap available for gcn_event: {dateobs}, notice_id: {notice_id}"
                            )

                        if not notified_on_skymap:
                            request_body = {
                                "target_class_name": "GcnNotice",
                                "target_id": notice_id,
                            }
                            post_notification(request_body, timeout=30)

                asyncio.run(_ingest())

        except Exception as e:
            traceback.print_exc()
            log.error(f"Failed to consume gcn event: {e}")


def service():
    if not is_configured():
        return
    while True:
        try:
            poll_events()
        except Exception as e:
            log.info(e)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log.error(f"Error: {e}")
