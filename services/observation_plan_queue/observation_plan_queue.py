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
        print("GOT HERE")
        if len(queue) == 0:
            time.sleep(5)
            continue
        plan, survey_efficiencies, user_id = queue.pop(0)
        print("GOT HERE 2")
        print(plan)
        print(survey_efficiencies)
        print(user_id)

        with DBSession() as session:
            try:
                plan_id = post_observation_plan(
                    plan, user_id, session, asynchronous=False
                )
            except Exception as e:
                log(f"Observation plan failed: {str(e)}")
                continue
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
            print("POST")
            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})

            print(data)

            user_id = data.get('user_id', None)
            plan = data.get('plan', None)
            survey_efficiencies = data.get('survey_efficiencies', [])

            if user_id is None:
                self.set_status(400)
                return self.write({"status": "error", "message": "Missing user_id"})
            if plan is None:
                self.set_status(400)
                return self.write({"status": "error", "message": "Missing plan"})

            try:
                user_id = int(user_id)
            except ValueError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Invalid user_id"})

            if not isinstance(plan, dict):
                self.set_status(400)
                return self.write({"status": "error", "message": "Invalid plan"})

            if not isinstance(survey_efficiencies, list):
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Invalid survey_efficiencies"}
                )
            if not all(
                isinstance(survey_efficiency, dict)
                for survey_efficiency in survey_efficiencies
            ):
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": "Invalid survey_efficiencies, not all elements are dicts",
                    }
                )

            print("PUTTING")

            try:
                # queue.put([plan, survey_efficiencies, user_id]
                # we want to put in the queue without blocking, as the queue might be busy
                # and we don't want to block the main thread
                queue.append([plan, survey_efficiencies, user_id])

                self.set_status(200)
                return self.write(
                    {
                        "status": "success",
                        "message": "Observation plans accepted into queue",
                        "data": {"queue_length": len(queue)},
                    }
                )
            except Exception as e:
                log(f"Error submitting observation plan: {str(e)}")
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Error processing observation plan"}
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
        port = cfg["ports"]["observation_plan_queue"]
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log("Current queue length: ", len(queue))
            time.sleep(60)
    except Exception as e:
        log(f"Error starting observation plan queue: {str(e)}")
        raise e
