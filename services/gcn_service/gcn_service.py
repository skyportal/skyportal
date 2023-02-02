from gcn_kafka import Consumer
import uuid

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.handlers.api.gcn import post_gcnevent_from_xml

from skyportal.models import (
    DBSession,
)

env, cfg = load_env()

init_db(**cfg['database'])

client_id = cfg['gcn.client_id']
client_secret = cfg['gcn.client_secret']
notice_types = [
    f'gcn.classic.voevent.{notice_type}' for notice_type in cfg["gcn.notice_types"]
]

log = make_log('gcnserver')


def service():
    if client_id is None or client_id == '':
        log('No client_id configured to poll gcn events (config: gcn.client_id')
        return
    if client_secret is None or client_secret == '':
        log('No client_secret configured to poll gcn events (config: gcn.client_secret')
        return
    if notice_types is None or notice_types == '' or notice_types == []:
        log('No notice_types configured to poll gcn events (config: gcn.notice_types')
        return

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
                user_id = 1
                with DBSession() as session:
                    post_gcnevent_from_xml(payload, user_id, session)

        except Exception as e:
            log(f'Failed to consume gcn event: {e}')


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f'Error: {e}')
