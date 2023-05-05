# For Michael, an example test run with Curl:
#
# curl -X POST http://localhost:64510 -d '{"method": "GET", "endpoint": "http://localhost:9980"}'
#

from datetime import datetime, timedelta
import time

import tornado.ioloop
import tornado.web
import asyncio
from tornado.ioloop import IOLoop
import tornado.escape
import json
import requests

import sqlalchemy as sa

from baselayer.app.models import init_db
from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    FollowupRequest,
    FacilityTransactionRequest,
)

env, cfg = load_env()
log = make_log('facility_queue')

init_db(**cfg['database'])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

WAIT_TIME_BETWEEN_QUERIES = timedelta(seconds=120)


class FacilityQueue(asyncio.Queue):
    async def load_from_db(self):
        # Load items from database into queue

        with DBSession() as session:
            requests = (
                session.query(FacilityTransactionRequest)
                .where(FacilityTransactionRequest.status != "complete")
                .all()
            )
            for req in requests:
                await self.put(req.id)

    async def service(self):
        while True:

            req_id = await queue.get()
            with DBSession() as session:
                req = session.query(FacilityTransactionRequest).get(req_id)
                dt = datetime.utcnow() - req.last_query
                if dt < WAIT_TIME_BETWEEN_QUERIES:
                    await self.put(req.id)
                else:
                    print(f"Executing request {req.id}")
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
                                log(f"Job with ID {req.id} completed")

                            elif json_response['starttimestamp']:
                                log(
                                    f"Job with ID {req.id} is running (started at {json_response['starttimestamp']})"
                                )
                                followup_request.status = f"Job is running (started at {json_response['starttimestamp']})"
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                await self.put(req.id)
                            else:
                                log(
                                    f"Waiting for job with ID {req.id} to start (queued at {json_response['timestamp']})"
                                )
                                followup_request.status = f"Waiting for job to start (queued at {json_response['timestamp']})"
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                await self.put(req.id)
                        else:
                            log(f"Job {req.id}: error: {response.content}")
                            followup_request.status = f'error: {response.content}'

                        session.add(followup_request)
                        session.commit()

                    else:
                        log(f'Job {req.id}: API for {instrument.name} unknown')

                # Pause between requests
                time.sleep(10)


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

        with DBSession() as session:

            current_req = session.execute(
                sa.select(FacilityTransactionRequest).where(
                    FacilityTransactionRequest.followup_request_id
                    == req.followup_request_id
                )
            ).first()
            if current_req is not None:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"Facility request {req.followup_request_id} already in the queue and/or complete",
                        "data": {"followup_request_id": req.followup_request_id},
                    }
                )

            endpoint_req = session.execute(
                sa.select(FacilityTransactionRequest).where(
                    FacilityTransactionRequest.endpoint == req.endpoint
                )
            ).first()
            if endpoint_req is not None:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"Facility request {req.followup_request_id} already reaches same endpoint {req.endpoint} as {endpoint_req.id}",
                        "data": {"followup_request_id": req.followup_request_id},
                    }
                )

            session.add(req)
            session.commit()

            await queue.put(req.id)

            self.set_status(200)
            return self.write(
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
