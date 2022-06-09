import gcn
from datetime import datetime, timedelta

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.handlers.api.gcn import post_gcnevent
from skyportal.handlers.api.observation_plan import post_observation_plan
from skyportal.models import DBSession, Allocation, GcnEvent

env, cfg = load_env()

init_db(**cfg['database'])

notice_types = [
    getattr(gcn.notice_types, notice_type) for notice_type in cfg["gcn_notice_types"]
]

gcn_observation_plans = [
    observation_plan for observation_plan in cfg["gcn_observation_plans"]
]

log = make_log('gcnserver')


def handle(payload, root):
    notice_type = gcn.get_notice_type(root)
    if notice_type in notice_types:
        user_id = 1
        with DBSession() as session:
            event_id = post_gcnevent(payload, user_id, session)
            event = session.query(GcnEvent).get(event_id)

            start_date = str(datetime.utcnow()).replace("T", "")
            end_date = str(datetime.utcnow() + timedelta(days=1)).replace("T", "")
            for gcn_observation_plan in gcn_observation_plans:
                proposal_id = gcn_observation_plan['allocation-proposal_id']
                allocation = (
                    session.query(Allocation)
                    .filter(Allocation.proposal_id == proposal_id)
                    .first()
                )

                if allocation is not None:
                    payload = {
                        **gcn_observation_plan['payload'],
                        'start_date': start_date,
                        'end_date': end_date,
                        'queue_name': f'{allocation.instrument.name}-{start_date}',
                    }
                    plan = {
                        'payload': payload,
                        'allocation_id': allocation.id,
                        'gcnevent_id': event.id,
                        'localization_id': event.localizations[-1].id,
                    }

                    post_observation_plan(plan, user_id, session)
                else:
                    log(f'No allocation with proposal_id {proposal_id}')


if __name__ == "__main__":
    gcn.listen(handler=handle)
