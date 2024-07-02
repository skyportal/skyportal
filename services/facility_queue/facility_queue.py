from astropy.time import Time, TimeDelta
import astropy.units as u
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

from baselayer.app.env import load_env
from baselayer.app.models import init_db
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
ZTF_PHOTOMETRY_CODES = {
    0: "Successful execution",
    56: "One or more epochs have photometry measurements that may be impacted by bad (including NaN'd) pixels",
    57: "One or more epochs had no reference image catalog source falling with 5 arcsec",
    58: "One or more epochs had a reference image PSF-catalog that does not exist in the archive",
    59: "One or more epochs may have suspect photometric uncertainties due to early creation date of difference image in production",
    60: "One or more epochs had upsampled diff-image PSF dimensions that were not odd integers",
    61: "One or more epochs had diff-image cutouts that were off the image or too close to an edge",
    62: "Requested start JD was before official survey start date [3/17/18] and was reset to 2018-03-17T00:00:00.0 UT",
    63: "No records (epochs) returned by database query",
    64: "Catastrophic error (see log output)",
    65: "Requested end JD is before official survey start date [3/17/18]",
    255: "Database connection or query execution error (see log output)",
}

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

WAIT_TIME_BETWEEN_QUERIES = timedelta(seconds=120)

queue = []


def service(queue):
    try:
        with DBSession() as session:
            cutoff_time = Time.now() - TimeDelta(3 * u.day)
            requests = (
                session.query(FacilityTransactionRequest)
                .where(
                    FacilityTransactionRequest.status != "complete",
                    FacilityTransactionRequest.status.not_like("error:%"),
                    FacilityTransactionRequest.created_at >= cutoff_time.datetime,
                )
                .all()
            )
            for req in requests:
                followup_request = session.scalars(
                    sa.select(FollowupRequest).where(
                        FollowupRequest.id == req.followup_request_id
                    )
                ).first()
                if followup_request is not None:
                    queue.append(req.id)
    except Exception as e:
        log(f"Error retrieving older requests: {e}")

    while True:
        if len(queue) == 0:
            # this is a retrieval queue service. Requests were sent before and
            # we are just waiting for the results. No rush to check the queue
            time.sleep(30)
            continue
        else:
            # we still add a sleep here to avoid hammering the DB
            time.sleep(5)
        req_id = queue.pop(0)
        if req_id is None:
            continue

        with DBSession() as session:
            try:
                req = session.scalars(
                    sa.select(FacilityTransactionRequest).where(
                        FacilityTransactionRequest.id == req_id
                    )
                ).first()
                if req is None:
                    log(
                        f"Facility transaction request {req_id} not found. Removing request {req_id} from queue."
                    )
                    continue

                dt = datetime.utcnow() - req.last_query
                if dt < WAIT_TIME_BETWEEN_QUERIES:
                    queue.append(req_id)
                else:
                    log(f"Executing request {req.id}")
                    followup_request = session.scalars(
                        sa.select(FollowupRequest).where(
                            FollowupRequest.id == req.followup_request_id
                        )
                    ).first()
                    if followup_request is None:
                        log(
                            f"Follow-up request {req.followup_request_id} not found. Removing request {req_id} from queue."
                        )
                        continue
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
                                followup_request.status = (
                                    "Committing photometry to database"
                                )
                                try:
                                    if json_response['result_url'] is not None:
                                        commit_photometry(
                                            json_response,
                                            altdata,
                                            followup_request.id,
                                            instrument.id,
                                            followup_request.requester.id,
                                            parent_session=session,
                                            duplicates="update",
                                        )
                                    req.status = 'complete'
                                    session.add(req)
                                    session.commit()
                                    log(f"Job with ID {req.id} completed")
                                    continue
                                except Exception as e:
                                    log(f"Error committing photometry: {str(e)}")
                                    status = f"error: {str(e)}"
                                    if followup_request.status != status:
                                        followup_request.status = status
                                        session.add(followup_request)
                                    req.status = f"error: {e}"
                                    session.add(req)
                                    session.commit()
                                    continue

                            elif json_response['starttimestamp']:
                                log(
                                    f"Job {req.id}: running (started at {json_response['starttimestamp']})"
                                )
                                status = f"Job is running (started at {json_response['starttimestamp']})"
                                if followup_request.status != status:
                                    followup_request.status = status
                                    session.add(followup_request)
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                session.commit()
                                queue.append(req_id)
                                log(f"Job {req.id}: {status}")
                            else:
                                status = f"Waiting for job to start (queued at {json_response['timestamp']})"
                                if followup_request.status != status:
                                    followup_request.status = status
                                    session.add(followup_request)
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                session.commit()
                                queue.append(req_id)
                                log(f"Job {req.id}: {status}")
                        else:
                            status = f"error: {response.content}"
                            if followup_request.status != status:
                                followup_request.status = status
                                session.add(followup_request)
                            req.last_query = datetime.utcnow()
                            session.add(req)
                            session.commit()
                            queue.append(req_id)
                            log(f"Job {req.id}: {status}")

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

                        if "Zero records returned" in str(response.text):
                            log(
                                "Found no records yet for this ZTF forced photometry account."
                            )
                            continue
                        elif response.status_code == 200:
                            df_result = pd.read_html(response.text)[0]
                            df_result.rename(
                                inplace=True,
                                columns={'startJD': 'jdstart', 'endJD': 'jdend'},
                            )
                            df_result = df_result.replace({np.nan: None})
                            if not set(keys).issubset(df_result.columns):
                                status = 'In progress: RA, Dec, jdstart, and jdend required in response.'
                                if followup_request.status != status:
                                    followup_request.status = status
                                    session.add(followup_request)
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                session.commit()
                                queue.append(req_id)
                                log(f'Job {req.id}: {status}')
                                continue

                            index_match = None
                            for index, row in df_result.iterrows():
                                if all(
                                    [
                                        np.isclose(row[key], req.data[key])
                                        for key in keys
                                    ]
                                ):
                                    index_match = index
                                    break
                            if index_match is None:
                                status = 'In progress: No matching response from forced photometry service. Waiting for database update.'
                                if followup_request.status != status:
                                    followup_request.status = status
                                    session.add(followup_request)
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                session.commit()
                                queue.append(req_id)
                                continue

                            row = df_result.loc[index_match]
                            if row['lightcurve'] is None:
                                status = 'In progress: Light curve not yet available. Waiting for it to complete.'
                                if followup_request.status != status:
                                    followup_request.status = status
                                    session.add(followup_request)
                                req.last_query = datetime.utcnow()
                                session.add(req)
                                session.commit()
                                queue.append(req_id)
                                log(f'Job {req.id}: {status}')
                                continue

                            lightcurve = row['lightcurve']
                            exitcode = row['exitcode']
                            exitcode_text = ZTF_PHOTOMETRY_CODES[exitcode]

                            if exitcode in [63, 64, 65, 255]:
                                status = f'No photometry available: {exitcode_text}'
                                if followup_request.status != status:
                                    followup_request.status = status
                                    session.add(followup_request)
                                req.last_query = datetime.utcnow()
                                req.status = 'complete'
                                session.add(req)
                                session.commit()
                                queue.append(req_id)
                                log(
                                    f"Job with ID {req.id} has no forced photometry: {exitcode_text}"
                                )
                            else:
                                dataurl = f"{ZTF_FORCED_URL}/{lightcurve}"
                                try:
                                    commit_photometry(
                                        dataurl,
                                        altdata,
                                        followup_request.id,
                                        instrument.id,
                                        followup_request.requester.id,
                                        parent_session=session,
                                        duplicates="update",
                                    )
                                    req.status = 'complete'
                                    session.add(req)
                                    session.commit()
                                    log(f"Job with ID {req.id} completed")
                                except Exception as e:
                                    if 'Failed to commit photometry' in str(e):
                                        status = f'error: {str(e)}'
                                    else:
                                        status = 'In progress: Light curve not yet available. Waiting for it to complete.'
                                    if followup_request.status != status:
                                        followup_request.status = status
                                        session.add(followup_request)
                                    req.last_query = datetime.utcnow()
                                    session.add(req)
                                    session.commit()
                                    queue.append(req_id)
                                    log(f'Job {req.id}: {status}')
                        elif (
                            'Error: database is busy; try again a minute later.'
                            in str(response.content)
                        ):
                            status = 'In progress: forced photometry database is busy; trying again in 2 minutes.'
                            if followup_request.status != status:
                                followup_request.status = status
                                session.add(followup_request)
                            req.last_query = datetime.utcnow()
                            session.add(req)
                            session.commit()
                            queue.append(req_id)
                            log(f'Job {req.id}: {status}')
                        else:
                            status = f'error: {response.content}'
                            if followup_request.status != status:
                                followup_request.status = status
                                session.add(followup_request)
                            req.last_query = datetime.utcnow()
                            session.add(req)
                            session.commit()
                            queue.append(req_id)
                            log(f'Job {req.id}: {status}')
                    else:
                        queue.append(req_id)
                        log(f'Job {req.id}: API for {instrument.name} unknown')
            except Exception as e:
                queue.append(req_id)
                log(f"Error processing follow-up request {req_id}: {str(e)}")
                try:
                    session.rollback()
                except Exception:
                    pass


def api(queue):
    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write({"status": "success", "data": {"queue_length": len(queue)}})

        async def post(self):
            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})

            try:
                queue.append(data["request_id"])
                self.set_status(200)
                return self.write(
                    {
                        "status": "success",
                        "message": "Facility request accepted into queue",
                        "data": {"queue_length": len(queue)},
                    }
                )
            except Exception as e:
                log(f"Error adding facility request to queue: {str(e)}")
                self.set_status(500)
                return self.write(
                    {
                        "status": "error",
                        "message": f"Error adding facility request to queue: {str(e)}",
                        "data": {"followup_request_id": data["followup_request_id"]},
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
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log(f"Current facility queue length: {len(queue)}")
            time.sleep(120)
            if not t.is_alive():
                log("Facility queue service thread died, restarting")
                t = Thread(target=service, args=(queue,))
                t.start()
            if not t2.is_alive():
                log("Facility queue API thread died, restarting")
                t2 = Thread(target=api, args=(queue,))
                t2.start()
    except Exception as e:
        log(f"Error starting facility queue: {str(e)}")
        raise e
