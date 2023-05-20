import os
import time
import uuid

import gcn
import lxml
import requests
import sqlalchemy as sa
import xmlschema
from gcn_kafka import Consumer

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.gcn import (
    get_tags,
    post_gcnevent_from_xml,
    post_skymap_from_notice,
)
from skyportal.models import DBSession, GcnEvent
from skyportal.utils.gcn import get_dateobs, get_skymap_metadata, get_trigger

env, cfg = load_env()

init_db(**cfg['database'])

client_id = cfg['gcn.client_id']
client_secret = cfg['gcn.client_secret']
notice_types = [
    f'gcn.classic.voevent.{notice_type}'
    for notice_type in cfg.get("gcn.notice_types", [])
]

reject_tags = cfg.get('gcn.reject_tags', [])

log = make_log('gcnserver')

user_id = 1

REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']

host = f'{cfg["server.protocol"]}://{cfg["server.host"]}' + (
    f':{cfg["server.port"]}' if cfg['server.port'] not in [80, 443] else ''
)


def is_loaded():
    try:
        r = requests.get(f'{host}/api/sysinfo', timeout=REQUEST_TIMEOUT_SECONDS)
    except:  # noqa: E722
        status_code = 0
    else:
        status_code = r.status_code

    if status_code == 200:
        return True
    else:
        return False


def service():
    if not is_configured():
        return
    while True:
        if is_loaded():
            try:
                poll_events()
            except Exception as e:
                log(e)
        time.sleep(15)


def get_root_from_payload(payload):
    schema = (
        f'{os.path.dirname(__file__)}/../../skyportal/utils/schema/VOEvent-v2.0.xsd'
    )
    voevent_schema = xmlschema.XMLSchema(schema)
    if voevent_schema.is_valid(payload):
        # check if is string
        try:
            payload = payload.encode('ascii')
        except AttributeError:
            pass
        root = lxml.etree.fromstring(payload)
    else:
        raise ValueError("xml file is not valid VOEvent")
    return root


def is_configured():
    if client_id is None or client_id == '':
        log('No client_id configured to poll gcn events (config: gcn.client_id')
        return False
    if client_secret is None or client_secret == '':
        log('No client_secret configured to poll gcn events (config: gcn.client_secret')
        return False
    if notice_types is None or notice_types == '' or notice_types == []:
        log('No notice_types configured to poll gcn events (config: gcn.notice_types')
        return False
    return True


def poll_events():
    client_group_id = cfg.get('gcn.client_group_id')
    if client_group_id is None or client_group_id == '':
        client_group_id = str(uuid.uuid4())

    config = {
        'group.id': client_group_id,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    }
    try:
        consumer = Consumer(
            config=config,
            client_id=client_id,
            client_secret=client_secret,
            domain=cfg['gcn.server'],
        )
    except Exception as e:
        log(f'Failed to initiate consumer to poll gcn events: {e}')
        return
    try:
        consumer.subscribe(notice_types)
    except Exception as e:
        log(f'Failed to subscribe to gcn events: {e}')
        return
    while True:
        try:
            for message in consumer.consume():
                payload = message.value()
                consumer.commit(message)
                if payload.find(b'Broker: Unknown topic or partition') != -1:
                    continue
                root = get_root_from_payload(payload)
                notice_type = gcn.get_notice_type(root)
                tags = get_tags(root)
                tags_intersection = list(set(tags).intersection(set(reject_tags)))
                if len(tags_intersection) > 0:
                    log(
                        f'Rejecting gcn_event from {message.topic()} due to tag(s): {tags_intersection}'
                    )
                    continue

                with DBSession() as session:
                    # we skip the ingestion of a retraction of the event does not exist in the DB
                    if notice_type == gcn.NoticeType.LVC_RETRACTION:
                        dateobs = get_dateobs(root)
                        trigger_id = get_trigger(root)
                        existing_event = None
                        if trigger_id:
                            existing_event = session.scalar(
                                sa.select(GcnEvent).where(
                                    GcnEvent.trigger_id == trigger_id
                                )
                            )
                        if not existing_event:
                            existing_event = session.scalar(
                                sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
                            )
                        if not existing_event:
                            log(
                                f'No event found to retract for gcn_event from {message.topic()}, skipping'
                            )
                            continue

                    # event ingestion
                    log(f'Ingesting gcn_event from {message.topic()}')
                    try:
                        dateobs, event_id, notice_id = post_gcnevent_from_xml(
                            payload,
                            user_id,
                            session,
                            post_skymap=False,
                            asynchronous=False,
                        )
                    except Exception as e:
                        log(f'Failed to ingest gcn_event from {message.topic()}: {e}')
                        continue

                    # skymap ingestion if available or cone
                    status, metadata = get_skymap_metadata(root, notice_type, 15)
                    if status in ['available', 'cone']:
                        log(
                            f'Ingesting skymap for gcn_event: {dateobs}, notice_id: {notice_id}'
                        )
                        try:
                            post_skymap_from_notice(
                                dateobs, notice_id, user_id, session, asynchronous=False
                            )
                        except Exception as e:
                            log(
                                f'Failed to ingest skymap for gcn_event: {dateobs}, notice_id: {notice_id}: {e}'
                            )
                    elif status == 'unavailable':
                        log(
                            f'No skymap available for gcn_event: {dateobs}, notice_id: {notice_id} with url: {metadata.get("url", None)}'
                        )
                    else:
                        log(
                            f'No skymap available for gcn_event: {dateobs}, notice_id: {notice_id}'
                        )

        except Exception as e:
            log(f'Failed to consume gcn event: {e}')


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f'Error: {e}')
