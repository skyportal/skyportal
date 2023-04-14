import asyncio
import json
import time
from threading import Thread

import requests
import tornado.escape
import tornado.ioloop
import tornado.web

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.observation_plan import (
    post_observation_plan,
    post_observation_plans,
    post_survey_efficiency_analysis,
)
from skyportal.models import DBSession

env, cfg = load_env()
log = make_log('observation_plan_queue')

init_db(**cfg['database'])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

queue = []


def service(queue):
    while True:
        if len(queue) == 0:
            time.sleep(1)
            continue
        plans, survey_efficiencies, combine_plans, default_plan, user_id = queue.pop(0)

        with DBSession() as session:
            try:
                plan_ids = []
                if len(plans) == 1:
                    plan_id = post_observation_plan(
                        plans[0],
                        user_id,
                        session,
                        default_plan=default_plan,
                        asynchronous=False,
                    )
                    plan_ids.append(plan_id)
                else:
                    if combine_plans:
                        plan_ids = post_observation_plans(
                            plans,
                            user_id,
                            session,
                            default_plan=default_plan,
                            asynchronous=False,
                        )
                    else:
                        for plan in plans:
                            plan_id = post_observation_plan(
                                plan,
                                user_id,
                                session,
                                default_plan=default_plan,
                                asynchronous=False,
                            )
                            plan_ids.append(plan_id)
            except Exception as e:
                log(f"Observation plan failed: {str(e)}")
                continue

            for plan_id in plan_ids:
                for survey_efficiency in survey_efficiencies:
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


def api(queue):
    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write({"status": "success", "data": {"queue_length": len(queue)}})

        def post(self):
            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})

            user_id = data.get('user_id', None)
            plans = data.get('plans', None)
            plan = data.get('plan', None)
            survey_efficiencies = data.get('survey_efficiencies', [])
            combine_plans = data.get('combine_plans', False)
            default_plan = data.get('default_plan', False)

            if user_id is None:
                self.set_status(400)
                return self.write({"status": "error", "message": "Missing user_id"})
            if plan is None and plans is None:
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Missing plan or plans"}
                )

            if plan is not None:
                plans = [plan]

            try:
                user_id = int(user_id)
            except ValueError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Invalid user_id"})

            if not isinstance(combine_plans, bool):
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Invalid combine_plans"}
                )

            if not isinstance(plans, list):
                self.set_status(400)
                return self.write({"status": "error", "message": "Invalid plans"})

            if not isinstance(survey_efficiencies, list):
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Invalid survey_efficiencies"}
                )

            for plan in plans:
                if not isinstance(plan, dict):
                    self.set_status(400)
                    return self.write({"status": "error", "message": "Invalid plan"})

            for survey_efficiency in survey_efficiencies:
                if not isinstance(survey_efficiency, dict):
                    self.set_status(400)
                    return self.write(
                        {
                            "status": "error",
                            "message": "Invalid survey_efficiencies, not all elements are dicts",
                        }
                    )

            try:
                queue.append(
                    [plans, survey_efficiencies, combine_plans, default_plan, user_id]
                )

                self.set_status(200)
                return self.write(
                    {
                        "status": "success",
                        "message": "Observation plan(s) accepted into queue",
                        "data": {"queue_length": len(queue)},
                    }
                )
            except Exception as e:
                log(f"Error submitting observation plan(s): {str(e)}")
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": "Error processing observation plan(s)",
                    }
                )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.observation_plan_queue"])
    loop.run_forever()


if __name__ == "__main__":
    try:
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log(f"Current obsplan queue length: {len(queue)}")
            time.sleep(120)
    except Exception as e:
        log(f"Error starting observation plan queue: {str(e)}")
        raise e
