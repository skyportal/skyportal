from gcn_kafka import Consumer
from datetime import datetime, timedelta
import sqlalchemy as sa
import uuid

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.handlers.api.gcn import post_gcnevent_from_xml
from skyportal.handlers.api.observation_plan import post_observation_plan
from skyportal.models import (
    DBSession,
    Allocation,
    DefaultObservationPlanRequest,
    GcnEvent,
)

env, cfg = load_env()

init_db(**cfg['database'])

client_id = cfg['gcn.client_id']
client_secret = cfg['gcn.client_secret']
notice_types = [
    f'gcn.classic.voevent.{notice_type}' for notice_type in cfg["gcn.notice_types"]
]
config_gcn_observation_plans_all = [
    observation_plan for observation_plan in cfg["gcn.observation_plans"]
]

log = make_log('gcnserver')

with DBSession() as session:
    config_gcn_observation_plans = []
    for config_gcn_observation_plan in config_gcn_observation_plans_all:
        allocation = session.scalars(
            sa.select(Allocation).where(
                Allocation.proposal_id
                == config_gcn_observation_plan["allocation-proposal_id"]
            )
        ).first()
        if allocation is not None:
            config_gcn_observation_plan["allocation_id"] = allocation.id
            config_gcn_observation_plans.append(config_gcn_observation_plan)


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
                    default_observation_plans = session.query(
                        DefaultObservationPlanRequest
                    ).all()
                    gcn_observation_plans = []
                    for plan in default_observation_plans:
                        allocation = (
                            session.query(Allocation)
                            .filter(Allocation.id == plan.allocation_id)
                            .first()
                        )

                        gcn_observation_plan = {}
                        gcn_observation_plan['allocation_id'] = allocation.id
                        gcn_observation_plan['payload'] = plan.payload
                        gcn_observation_plans.append(gcn_observation_plan)
                    gcn_observation_plans = (
                        gcn_observation_plans + config_gcn_observation_plans
                    )

                    event_id = post_gcnevent_from_xml(payload, user_id, session)
                    event = session.query(GcnEvent).get(event_id)
                    localizations = sorted(
                        (loc.to_dict() for loc in event.localizations),
                        key=lambda x: x["created_at"],
                        reverse=True,
                    )

                    start_date = str(datetime.utcnow()).replace("T", "")
                    end_date = str(datetime.utcnow() + timedelta(days=1)).replace(
                        "T", ""
                    )
                    for ii, gcn_observation_plan in enumerate(gcn_observation_plans):
                        allocation_id = gcn_observation_plan['allocation_id']
                        allocation = (
                            session.query(Allocation)
                            .filter(Allocation.id == allocation_id)
                            .first()
                        )

                        if allocation is not None:
                            payload = {
                                **gcn_observation_plan['payload'],
                                'start_date': start_date,
                                'end_date': end_date,
                                'queue_name': f'{allocation.instrument.name}-{start_date}-{ii}',
                            }
                            plan = {
                                'payload': payload,
                                'allocation_id': allocation.id,
                                'gcnevent_id': event.id,
                                'localization_id': localizations[0]["id"],
                            }

                            post_observation_plan(plan, user_id, session)
                        else:
                            log(f'No allocation with allocation_id {allocation_id}')

        except Exception as e:
            log(f'Failed to consume gcn event: {e}')


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f'Error: {e}')
