import tornado.ioloop
import tornado.web
import asyncio
from tornado.ioloop import IOLoop
import tornado.escape
import json
import requests

from baselayer.app.models import init_db
from baselayer.app.env import load_env
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


class ObservationPlansQueue(asyncio.Queue):
    async def service(self):
        while True:

            plan, survey_efficiencies, user_id = await queue.get()
            if plan is None:
                continue

            with DBSession() as session:
                plan_id = post_observation_plan(
                    plan, user_id, session, asynchronous=False
                )
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

        plan = data['plan']
        survey_efficiencies = data['survey_efficiencies']
        user_id = data['user_id']

        try:
            await queue.put([plan, survey_efficiencies, user_id])

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
                {"status": "error", "message": "Error processing observation plan"}
            )


if __name__ == "__main__":
    app = tornado.web.Application([(r"/", QueueHandler)])
    app.listen(cfg["ports.observation_plan_queue"])

    loop = IOLoop.current()
    loop.add_callback(queue.service)
    loop.start()
