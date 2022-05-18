# For Michael, an example test run with Curl:
#
# curl -X POST http://localhost:64510 -d '{"method": "GET", "endpoint": "http://localhost:9980"}'
#

import tornado.ioloop
import tornado.web
import asyncio
from tornado.ioloop import IOLoop
import tornado.escape
import json
import requests

from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy as sa

from baselayer.app.models import init_db
from baselayer.app.env import load_env
from skyportal.models import (
    DBSession,
    FollowupRequest,
    FacilityTransactionRequest,
)

env, cfg = load_env()

init_db(**cfg['database'])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

# class FacilityTransactionRequest:
#    def __init__(self, method=None, endpoint=None, headers=None):
#        self.method = method
#        self.endpoint = endpoint
#        self.headers = headers

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


class FacilityQueue(asyncio.Queue):
    async def load_from_db(self):
        # Load items from database into queue

        session = Session()
        requests = (
            session.query(FacilityTransactionRequest)
            .where(FacilityTransactionRequest.status != "complete")
            .all()
        )
        for req in requests:
            await self.put(req)

    async def service(self):
        while True:
            req = await queue.get()
            print(f"{req.method} request to [{req.endpoint}]")

            session = Session()
            followup_request = session.query(FollowupRequest).get(
                req.followup_request_id
            )
            instrument = followup_request.allocation.instrument
            altdata = followup_request.allocation.altdata

            response = request_session.request(
                req.method,
                req.endpoint,
                json=req.data,
                params=req.params,
                headers=req.headers,
            )

            if instrument.name == "ATLAS":
                from skyportal.facility_apis.atlas import commit_photometry

                if response.status_code == 200:
                    try:
                        json_response = response.json()
                    except Exception:
                        raise ('No JSON data returned in request')

                    if json_response['finishtimestamp']:
                        req.status = "Committing photometry to database"
                        commit_photometry(
                            json_response,
                            altdata,
                            followup_request.id,
                            instrument.id,
                            followup_request.requester.id,
                        )
                        req.status = 'complete'
                        session.add(req)

                    elif json_response['starttimestamp']:
                        followup_request.status = f"Task is running (started at {json_response['starttimestamp']})"
                        await self.put(req)
                    else:
                        followup_request.status = f"Waiting for job to start (queued at {json_response['timestamp']})"
                        await self.put(req)
                else:
                    followup_request.status = f'error: {response.content}'

                session.add(followup_request)
                session.commit()

            else:
                raise ValueError(f'API for {instrument.name} unknown')

            # Simulate time taken to service this request
            await asyncio.sleep(3)

            print(f"{req.method} request to [{req.endpoint}] completed")


queue = FacilityQueue()


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

        # validate data here and return 400 if invalid
        try:
            req = FacilityTransactionRequest(**data)
        except TypeError:
            self.set_status(400)
            return self.write(
                {
                    "status": "error",
                    "message": "Invalid arguments; cannot construct facility request",
                }
            )

        for field in ('method', 'endpoint'):
            if getattr(req, field) is None:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"Missing request attribute `{field}`",
                    }
                )

        session = Session()

        current_req = session.execute(
            sa.select(FacilityTransactionRequest).where(
                FacilityTransactionRequest.followup_request_id
                == req.followup_request_id
            )
        ).first()
        if current_req is not None:
            self.write(
                {
                    "status": "error",
                    "message": f"Facility request {req.followup_request_id} already in the queue and/or complete",
                    "data": {"followup_request_id": req.followup_request_id},
                }
            )
            return

        session.add(req)
        session.commit()

        await queue.put(req)

        self.write(
            {
                "status": "success",
                "message": "Facility request accepted into queue",
                "data": {"queue_length": queue.qsize()},
            }
        )


if __name__ == "__main__":
    app = tornado.web.Application([(r"/", QueueHandler)])
    app.listen(cfg["ports.facility_queue"])

    loop = IOLoop.current()
    loop.add_callback(queue.load_from_db)
    loop.add_callback(queue.service)
    loop.start()
