from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from threading import Thread
import time

import tornado.ioloop
import tornado.web
import asyncio
import tornado.escape
import json
import requests
from requests.auth import HTTPBasicAuth

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

ZTF_FORCED_URL = cfg['app.ztf_forced_endpoint']

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

WAIT_TIME_BETWEEN_QUERIES = timedelta(seconds=10)

queue = []


def retrieve_old_requests():
    with DBSession() as session:
        requests = (
            session.query(FacilityTransactionRequest)
            .where(FacilityTransactionRequest.status != "complete")
            .all()
        )
        for req in requests:
            queue.append(req.id)


def service(queue):
    while True:
        if len(queue) == 0:
            time.sleep(1)
            continue
        req_id = queue.pop(0)
        if req_id is None:
            continue

        try:
            execute_request(req_id)
        except Exception as e:
            log(f"Error processing follow-up request {req_id}: {str(e)}")


def execute_request(req_id):
    with DBSession() as session:
        req = session.query(FacilityTransactionRequest).get(req_id)
        dt = datetime.utcnow() - req.last_query
        if dt < WAIT_TIME_BETWEEN_QUERIES:
            queue.append(req.id)
        else:
            log(f"Executing request {req.id}")
            followup_request = session.query(FollowupRequest).get(
                req.followup_request_id
            )
            instrument = followup_request.allocation.instrument
            altdata = followup_request.allocation.altdata

            if instrument.name == "ATLAS":
                from skyportal.facility_apis.atlas import commit_photometry

                response = request_session.request(
                    req.method,
                    req.endpoint,
                    json=req.data,
                    params=req.params,
                    headers=req.headers,
                )

                if response.status_code == 200:
                    try:
                        json_response = response.json()
                    except Exception:
                        raise ('No JSON data returned in request')

                    if json_response['finishtimestamp']:
                        followup_request.status = "Committing photometry to database"
                        commit_photometry(
                            json_response,
                            altdata,
                            followup_request.id,
                            instrument.id,
                            followup_request.requester.id,
                        )
                        followup_request.status = 'complete'
                        req.status = 'complete'
                        session.add(req)
                        log(f"Job with ID {req.id} completed")

                    elif json_response['starttimestamp']:
                        log(
                            f"Job {req.id}: running (started at {json_response['starttimestamp']})"
                        )
                        followup_request.status = f"Job is running (started at {json_response['starttimestamp']})"
                        req.last_query = datetime.utcnow()
                        session.add(req)
                        queue.append(req.id)
                    else:
                        log(
                            f"Job {req.id}: Waiting for job to start (queued at {json_response['timestamp']})"
                        )
                        followup_request.status = f"Waiting for job to start (queued at {json_response['timestamp']})"
                        req.last_query = datetime.utcnow()
                        session.add(req)
                        queue.append(req.id)
                else:
                    log(f"Job {req.id}: error: {response.content}")
                    followup_request.status = f'error: {response.content}'

                session.add(followup_request)
                session.commit()
            elif instrument.name == "ZTF":
                from skyportal.facility_apis.ztf import commit_photometry

                keys = ['ra', 'dec', 'jdstart', 'jdend']

                response = request_session.request(
                    req.method,
                    req.endpoint,
                    json=req.data,
                    params=req.params,
                    headers=req.headers,
                    auth=HTTPBasicAuth(
                        altdata['ipac_http_user'], altdata['ipac_http_password']
                    ),
                )

                if response.status_code == 200:
                    df_result = pd.read_html(response.text)[0]
                    df_result.rename(
                        inplace=True, columns={'startJD': 'jdstart', 'endJD': 'jdend'}
                    )
                    df_result = df_result.replace({np.nan: None})
                    if not set(keys).issubset(df_result.columns):
                        status = 'In progress: RA, Dec, jdstart, and jdend required in response.'
                        followup_request.status = status
                        log(f'Job {req.id}: {status}')
                        req.last_query = datetime.utcnow()
                        session.add(req)
                        session.commit()
                        queue.append(req.id)
                        return

                    index_match = None
                    for index, row in df_result.iterrows():
                        if not all(
                            [np.isclose(row[key], req.data[key]) for key in keys]
                        ):
                            continue
                        index_match = index
                    if index_match is None:
                        status = 'In progress: No matching response from forced photometry service. Waiting for database update.'
                        followup_request.status = status
                        log(f'Job {req.id}: {status}')
                        req.last_query = datetime.utcnow()
                        session.add(req)
                        session.commit()
                        queue.append(req.id)
                        return
                    else:
                        row = df_result.loc[index_match]
                        if row['lightcurve'] is None:
                            status = 'In progress: Light curve not yet available. Waiting for it to complete.'
                            followup_request.status = status
                            log(f'Job {req.id}: {status}')
                            req.last_query = datetime.utcnow()
                            session.add(req)
                            session.commit()
                            queue.append(req.id)
                            return
                        else:
                            lightcurve = row['lightcurve']
                            dataurl = f"{ZTF_FORCED_URL}/{lightcurve}"
                            commit_photometry(
                                dataurl,
                                altdata,
                                req.id,
                                instrument.id,
                                followup_request.requester.id,
                            )
                            req.status = 'complete'
                            session.add(req)

                else:
                    status = f'error: {response.content}'
                    followup_request.status = status
                    log(f'Job {req.id}: {status}')
                    req.last_query = datetime.utcnow()
                    session.add(req)
                    queue.append(req.id)

                session.add(followup_request)
                session.commit()
            else:
                log(f'Job {req.id}: API for {instrument.name} unknown')
                queue.append(req.id)


def api(queue):
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

                queue.append(req.id)

                self.set_status(200)
                return self.write(
                    {
                        "status": "success",
                        "message": "Facility request accepted into queue",
                        "data": {"queue_length": len(queue)},
                    }
                )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.facility_queue"])
    loop.run_forever()


if __name__ == "__main__":
    try:
        retrieve_old_requests()

        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log(f"Current facility queue length: {len(queue)}")
            time.sleep(120)
    except Exception as e:
        log(f"Error starting facility queue: {str(e)}")
        raise e
