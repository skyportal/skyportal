import json
import traceback
import os
import uuid

import gcn
import lxml
import sqlalchemy as sa
import xmlschema
from gcn_kafka import Consumer

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.gcn import (
    get_tags,
    get_json_tags,
    post_gcnevent_from_xml,
    post_gcnevent_from_json,
    post_skymap_from_notice,
)
from skyportal.models import DBSession, GcnEvent
from skyportal.utils.gcn import get_dateobs, get_skymap_metadata, get_trigger
from skyportal.utils.notifications import post_notification
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg['database'])

client_id = cfg['gcn.client_id']
client_secret = cfg['gcn.client_secret']
voevent_notice_types = [
    f'gcn.classic.voevent.{notice_type}'
    for notice_type in cfg.get("gcn.notice_types", [])
]
json_notice_types = [
    f'gcn.notices.{notice_type}' for notice_type in cfg.get("gcn.json_notice_types", [])
]

reject_tags = cfg.get('gcn.reject_tags', [])

log = make_log('gcnserver')

user_id = 1


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
    if (
        voevent_notice_types is None
        or voevent_notice_types == ''
        or voevent_notice_types == []
    ) and (
        json_notice_types is None or json_notice_types == '' or json_notice_types == []
    ):
        log(
            'No notice_types configured to poll gcn events (config: gcn.notice_types and/or gcn.json_notice_types)'
        )
        return False
    return True


@check_loaded(logger=log)
def poll_events(*args, **kwargs):
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
        consumer.subscribe(voevent_notice_types + json_notice_types)
    except Exception as e:
        log(f'Failed to subscribe to gcn events: {e}')
        return
    while True:
        try:
            for message in consumer.consume():
                payload = message.value()
                topic = message.topic()
                consumer.commit(message)

                if payload is None:
                    continue

                if payload.find(b'Broker: Unknown topic or partition') != -1:
                    continue

                # initialize some variables tht will be used later
                root, notice_type, tags, alert_type = None, None, None, None
                dateobs, event_id, notice_id = None, None, None

                try:  # try xml first
                    root = get_root_from_payload(payload)
                    notice_type = gcn.get_notice_type(root)
                    tags = get_tags(root)
                    alert_type = "voevent"
                except Exception:  # then json
                    payload = json.loads(payload.decode('utf8'))
                    payload['notice_type'] = topic.replace("gcn.notices.", "")
                    notice_type = None
                    tags = get_json_tags(payload)
                    alert_type = "json"

                    if (
                        payload['notice_type']
                        == "gcn.notices.icecube.lvk_nu_track_search"
                    ):
                        # 3 sigma
                        if payload.get("pval_bayesian", 1) > 0.003:
                            continue

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
                        if trigger_id is not None:
                            existing_event = session.scalar(
                                sa.select(GcnEvent).where(
                                    GcnEvent.trigger_id == trigger_id
                                )
                            )
                        if existing_event is None and dateobs is not None:
                            existing_event = session.scalar(
                                sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
                            )
                        if existing_event is None:
                            log(
                                f'No event found to retract for gcn_event from {message.topic()}, skipping'
                            )
                            continue

                    # event ingestion
                    log(f'Ingesting gcn_event from {message.topic()}')
                    try:
                        if alert_type == "voevent":
                            dateobs, event_id, notice_id = post_gcnevent_from_xml(
                                payload,
                                user_id,
                                session,
                                post_skymap=False,
                                asynchronous=False,
                                notify=False,
                            )
                        elif alert_type == "json":
                            dateobs, event_id, notice_id = post_gcnevent_from_json(
                                payload,
                                user_id,
                                session,
                                asynchronous=False,
                            )
                    except Exception as e:
                        traceback.print_exc()
                        log(f'Failed to ingest gcn_event from {message.topic()}: {e}')
                        continue

                    # TODO: unify skymap ingestion to also process JSON notices sky maps
                    # after ingesting the event (to deal with timeouts better)
                    notified_on_skymap = False
                    if alert_type == "voevent":
                        # skymap ingestion if available or cone
                        status, metadata = get_skymap_metadata(root, notice_type, 15)
                        if status in ['available', 'cone']:
                            log(
                                f'Ingesting skymap for gcn_event: {dateobs}, notice_id: {notice_id}'
                            )
                            try:
                                localization_id = post_skymap_from_notice(
                                    dateobs,
                                    notice_id,
                                    user_id,
                                    session,
                                    asynchronous=False,
                                    notify=False,
                                )
                                request_body = {
                                    'target_class_name': 'Localization',
                                    'target_id': localization_id,
                                }
                                notified_on_skymap = post_notification(
                                    request_body, timeout=30
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
                    else:
                        # for now we don't store notices of JSON type, because we are missing
                        # the notice_type int -> text mapping (and the ivorn) from pygcn
                        # so we can't notify using our current notification system
                        notified_on_skymap = True
                    if not notified_on_skymap:
                        request_body = {
                            'target_class_name': 'GcnNotice',
                            'target_id': notice_id,
                        }
                        post_notification(request_body, timeout=30)

        except Exception as e:
            traceback.print_exc()
            log(f'Failed to consume gcn event: {e}')


def service():
    if not is_configured():
        return
    while True:
        try:
            poll_events()
        except Exception as e:
            log(e)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f'Error: {e}')
