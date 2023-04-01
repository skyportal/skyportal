from astropy.time import Time
from datetime import datetime, timedelta
import gcn

import tornado.ioloop
import tornado.web
import asyncio
from tornado.ioloop import IOLoop
import tornado.escape
import json
import operator  # noqa: F401
import requests
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.models import init_db
from baselayer.app.env import load_env
from baselayer.log import make_log

from skyportal.handlers.api.observation_plan import (
    post_observation_plan,
    post_survey_efficiency_analysis,
)
from skyportal.models import (
    DBSession,
    Allocation,
    DefaultObservationPlanRequest,
    GcnEvent,
    Localization,
    LocalizationTag,
    User,
)

env, cfg = load_env()
log = make_log('observation_plan_queue')

init_db(**cfg['database'])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)


class ObservationPlansQueue(asyncio.Queue):
    async def service(self):
        while True:

            localization_id, user_id = await queue.get()
            if localization_id is None:
                continue
            if user_id is None:
                continue

            with DBSession() as session:
                user = session.scalar(sa.select(User).where(User.id == user_id))
                localization = session.query(Localization).get(localization_id)
                localization_tags = [
                    tags.text
                    for tags in session.query(LocalizationTag)
                    .filter(LocalizationTag.localization_id == localization_id)
                    .all()
                ]
                dateobs = localization.dateobs
                config_gcn_observation_plans_all = [
                    observation_plan
                    for observation_plan in cfg["gcn.observation_plans"]
                ]
                config_gcn_observation_plans = []
                for config_gcn_observation_plan in config_gcn_observation_plans_all:
                    allocation = session.scalars(
                        Allocation.select(user).where(
                            Allocation.proposal_id
                            == config_gcn_observation_plan["allocation-proposal_id"]
                        )
                    ).first()
                    if allocation is not None:
                        allocation_id = allocation.id
                        config_gcn_observation_plan["allocation_id"] = allocation_id
                        config_gcn_observation_plan["survey_efficiencies"] = []
                        config_gcn_observation_plans.append(config_gcn_observation_plan)
                    else:
                        allocation_id = None

                default_observation_plans = (
                    (
                        session.scalars(
                            DefaultObservationPlanRequest.select(
                                user,
                                options=[
                                    joinedload(
                                        DefaultObservationPlanRequest.default_survey_efficiencies
                                    )
                                ],
                            )
                        )
                    )
                    .unique()
                    .all()
                )
                gcn_observation_plans = []
                for plan in default_observation_plans:
                    allocation = session.scalars(
                        Allocation.select(user).where(
                            Allocation.id == plan.allocation_id
                        )
                    ).first()

                    gcn_observation_plan = {
                        'allocation_id': allocation_id,
                        'filters': plan.filters,
                        'payload': plan.payload,
                        'survey_efficiencies': [
                            survey_efficiency.to_dict()
                            for survey_efficiency in plan.default_survey_efficiencies
                        ],
                    }
                    gcn_observation_plans.append(gcn_observation_plan)
                gcn_observation_plans = (
                    gcn_observation_plans + config_gcn_observation_plans
                )

                event = session.scalars(
                    GcnEvent.select(user).where(GcnEvent.dateobs == dateobs)
                ).first()
                start_date = str(datetime.utcnow()).replace("T", "")

                for ii, gcn_observation_plan in enumerate(gcn_observation_plans):
                    allocation_id = gcn_observation_plan['allocation_id']
                    allocation = session.scalars(
                        Allocation.select(user).where(Allocation.id == allocation_id)
                    ).first()

                    if allocation is not None:

                        end_date = allocation.instrument.telescope.next_sunrise()
                        if end_date is None:
                            end_date = str(
                                datetime.utcnow() + timedelta(days=1)
                            ).replace("T", "")
                        else:
                            end_date = Time(end_date, format='jd').iso

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
                            'localization_id': localization_id,
                        }

                        if 'filters' in gcn_observation_plan:
                            filters = gcn_observation_plan['filters']
                            if filters is not None:
                                if (
                                    'gcn_notices' in filters
                                    and len(filters['gcn_notices']) > 0
                                ):
                                    if not any(
                                        [
                                            gcn.NoticeType(notice.notice_type).name
                                            in filters['gcn_notices']
                                            for notice in event.gcn_notices
                                        ]
                                    ):
                                        continue

                                if (
                                    'gcn_tags' in filters
                                    and len(filters['gcn_tags']) > 0
                                ):
                                    intersection = list(
                                        set(event.tags) & set(filters["gcn_tags"])
                                    )
                                    if len(intersection) == 0:
                                        continue

                                if (
                                    "localization_tags" in filters
                                    and len(filters["localization_tags"]) > 0
                                ):
                                    intersection = list(
                                        set(localization_tags)
                                        & set(filters["localization_tags"])
                                    )
                                    if len(intersection) == 0:
                                        continue

                        plan_id = post_observation_plan(
                            plan, user_id, session, asynchronous=False
                        )
                        for survey_efficiency in gcn_observation_plan[
                            'survey_efficiencies'
                        ]:
                            try:
                                post_survey_efficiency_analysis(
                                    survey_efficiency,
                                    plan_id,
                                    user_id,
                                    session,
                                    asynchronous=False,
                                )
                            except Exception as e:
                                log(f"Survey efficiency analysis failed: {str(e)}")
                                continue


queue = ObservationPlansQueue()


class QueueHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write({"status": "success", "data": {"queue_length": queue.qsize()}})

    async def post(self):

        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            return self.write({"status": "error", "message": "Malformed JSON data"})

        localization_id = data['localization_id']
        user_id = data['user_id']

        try:
            await queue.put([localization_id, user_id])

            self.set_status(200)
            return self.write(
                {
                    "status": "success",
                    "message": "Observation plans accepted into queue",
                    "data": {"queue_length": queue.qsize()},
                }
            )
        except Exception as e:
            log(f"Error processing notification: {str(e)}")
            DBSession().rollback()
            self.set_status(400)
            return self.write(
                {"status": "error", "message": "Error processing notification"}
            )


if __name__ == "__main__":
    app = tornado.web.Application([(r"/", QueueHandler)])
    app.listen(cfg["ports.observation_plan_queue"])

    loop = IOLoop.current()
    loop.add_callback(queue.service)
    loop.start()
