import asyncio
import json
import time
import urllib
from threading import Thread
from datetime import datetime, timedelta

import requests
import sqlalchemy as sa
import tornado.escape
import tornado.ioloop
import tornado.web
from sqlalchemy.orm import scoped_session, sessionmaker
import conesearch_alchemy as ca

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.app.flow import Flow
from baselayer.log import make_log
from skyportal.handlers.api.photometry import add_external_photometry
from skyportal.handlers.api.source import post_source
from skyportal.handlers.api.spectrum import post_spectrum
from skyportal.models import DBSession, Obj, User, Group
from skyportal.utils.tns import (
    get_IAUname,
    read_tns_photometry,
    read_tns_spectrum,
    get_recent_TNS,
)

env, cfg = load_env()
log = make_log('tns_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

USER_ID = 1  # super admin user ID
DEFAULT_RADIUS = 2.0 / 3600  # 2 arcsec in degrees

TNS_URL = cfg['app.tns.endpoint']
object_url = urllib.parse.urljoin(TNS_URL, 'api/get/object')
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')

bot_id = cfg.get('app.tns.bot_id', None)
bot_name = cfg.get('app.tns.bot_name', None)
api_key = cfg.get('app.tns.api_key', None)
look_back_days = cfg.get('app.tns.look_back_days', 1)

queue = []


def add_tns_name_to_existing_objs(tns_name, tns_source_data, tns_ra, tns_dec, session):
    """Add TNS name to existing objects within 2 arcseconds of the TNS position.

    Parameters
    ----------
    tns_name : str
        TNS name to be added to the object
    tns_source_data : dict
        TNS source data to be added to the object as tns_info
    tns_ra : float
        Right ascension of the TNS source
    tns_dec : float
        Declination of the TNS source
    session : `sqlalchemy.orm.session.Session`
        Database session object
    """
    tns_name = str(tns_name).strip()
    other = ca.Point(ra=tns_ra, dec=tns_dec)
    existing_objs = session.scalars(
        sa.select(Obj).where(Obj.within(other, DEFAULT_RADIUS))  # 2 arcseconds
    ).all()
    if len(existing_objs) > 0:
        for obj in existing_objs:
            try:
                if obj.tns_name == tns_name:
                    continue
                elif obj.tns_name is None or obj.tns_name == "":
                    obj.tns_name = tns_name
                    obj.tns_info = tns_source_data
                # if the current name doesn't have the SN designation but the new name has it, update
                elif not str(obj.tns_name).lower().strip().startswith(
                    "sn"
                ) and "AT" not in str(tns_name):
                    obj.tns_name = str(tns_name).strip()
                    obj.tns_info = tns_source_data
                else:
                    continue

                session.commit()
                log(f"Updated object {obj.id} with TNS name {tns_name}")
                flow = Flow()
                flow.push(
                    '*',
                    'skyportal/REFRESH_SOURCE',
                    payload={'obj_key': obj.internal_key},
                )
            except Exception as e:
                log(f"Error updating object: {str(e)}")
                session.rollback()


def service(queue):
    """Process the TNS retrieval queue

    Parameters
    ----------
    queue : list
        List of tasks to be processed
    """
    if TNS_URL is None or bot_id is None or bot_name is None or api_key is None:
        log("TNS watcher not configured, skipping")
        return
    tns_headers = {
        "User-Agent": f'tns_marker{{"tns_id": {bot_id},"type": "bot", "name": "{bot_name}"}}',
    }

    while True:
        if len(queue) == 0:
            time.sleep(1)
            continue
        task = queue.pop(0)
        if task is None:
            continue

        tns_source = None
        existing_obj = None
        tns_name = None
        public_group_id = None

        try:
            with DBSession() as session:
                # verify that the public group exists
                public_group = session.scalar(
                    sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
                )
                if public_group is None:
                    log(
                        f"WARNING: Public group {cfg['misc.public_group_name']} not found in the database, stopping TNS watcher"
                    )
                    return
                public_group_id = public_group.id

                if task.get("obj_id") is not None:
                    # here we are looking for the TNS name of an existing object
                    # to add the TNS name to the object + create a TNS source
                    existing_obj = session.scalar(
                        sa.select(Obj).where(Obj.id == task.get("obj_id"))
                    )
                    if existing_obj is None:
                        log(
                            f"Object {task['obj_id']} not found in the database, skipping"
                        )
                        continue

                    # find the most recent object on TNS within a certain radius (default 2 arcsec) of the object
                    tns_prefix, tns_name = get_IAUname(
                        api_key,
                        tns_headers,
                        ra=existing_obj.ra,
                        dec=existing_obj.dec,
                        radius=float(task.get("radius", DEFAULT_RADIUS)),
                    )
                    if tns_name is None:
                        raise ValueError(f'{task.get("obj_id")} not found on TNS.')
                    tns_source = f"{tns_prefix} {tns_name}"
                elif (
                    task.get("tns_name") is not None
                    and task.get("tns_prefix") is not None
                ):
                    # here we just want to create a TNS source
                    tns_name = task.get("tns_name")
                    tns_source = f"{task.get('tns_prefix')} {task.get('tns_name')}"
                else:
                    log("No obj_id or tns_name provided, skipping")
                    continue

                # fetch the data from TNS
                data = {
                    'api_key': api_key,
                    'data': json.dumps(
                        {
                            "objname": tns_name,
                            "photometry": 1,
                            "spectra": 1,
                        }
                    ),
                }
                status_code = 429
                n_retries = 0
                r = None
                while (
                    status_code == 429 and n_retries < 24
                ):  # 6 * 4 * 10 seconds = 4 minutes of retries
                    r = requests.post(
                        object_url,
                        headers=tns_headers,
                        data=data,
                        allow_redirects=True,
                        stream=True,
                        timeout=10,
                    )
                    status_code = r.status_code
                    if status_code == 429:
                        n_retries += 1
                        time.sleep(10)
                    else:
                        break
                if not isinstance(r, requests.Response):
                    log(f"Error getting TNS data for {tns_source}: no response")
                    continue
                if status_code != 200:
                    log(f"Error getting TNS data for {tns_source}: {r.text}")
                    continue

                tns_source_data = r.json().get("data", dict()).get("reply", dict())
                if tns_source_data is None:
                    log(f"Error getting TNS data for {tns_source}: no reply in data")
                    continue

                ra, dec = tns_source_data.get("radeg", None), tns_source_data.get(
                    "decdeg", None
                )
                if ra is None or dec is None:
                    log(f"Error processing TNS source {tns_source}: no coordinates")
                    continue

                if existing_obj is not None:
                    # if were looking for the TNS name of an existing source,
                    # simply add the TNS name to the existing object
                    existing_obj.tns_name = tns_source
                    existing_obj.tns_info = tns_source_data
                else:
                    # otherwise, add the TNS name to all the existing sources within a 2 arcsec radius
                    add_tns_name_to_existing_objs(
                        tns_source, tns_source_data, ra, dec, session
                    )

                with DBSession() as session:
                    existing_tns_obj = session.scalar(
                        sa.select(Obj).where(Obj.id == tns_name)
                    )
                    if existing_tns_obj is None:
                        # we add the TNS source to the database if it doesn't exist yet
                        # with its photometry and spectra
                        new_source_data = {
                            "id": tns_name,
                            "ra": ra,
                            "dec": dec,
                            "tns_name": tns_source,
                            "tns_info": tns_source_data,
                        }
                        post_source(new_source_data, USER_ID, session)

                        user = session.scalar(sa.select(User).where(User.id == USER_ID))
                        if user is None:
                            log(
                                f"Error getting user {USER_ID}, required to add photometry with add_external_photometry()"
                            )
                            continue

                        photometry = tns_source_data.get('photometry', [])
                        if len(photometry) == 0:
                            log(f"No photometry found on TNS for source {tns_source}")
                            continue
                        failed_photometry = []
                        failed_photometry_errors = []
                        for phot in photometry:
                            read_photometry = False
                            try:
                                df, instrument_id = read_tns_photometry(phot, session)
                                data_out = {
                                    'obj_id': tns_name,
                                    'instrument_id': instrument_id,
                                    'group_ids': [public_group_id],
                                    **df.to_dict(orient='list'),
                                }
                                read_photometry = True
                            except Exception as e:
                                failed_photometry.append(phot)
                                failed_photometry_errors.append(str(e))
                                log(f'Cannot read TNS photometry {str(phot)}: {str(e)}')
                                continue
                            if read_photometry:
                                try:
                                    add_external_photometry(
                                        data_out, user, parent_session=session
                                    )
                                except Exception as e:
                                    failed_photometry.append(phot)
                                    failed_photometry_errors.append(str(e))
                                    continue

                        if len(failed_photometry) > 0:
                            log(
                                f'Failed to retrieve {len(failed_photometry)}/{len(photometry)} TNS photometry points from {tns_source}: {str(list(set(failed_photometry_errors)))}'
                            )
                        else:
                            log(
                                f'Successfully retrieved {len(photometry)} TNS photometry points from {tns_source}'
                            )

                        spectra = tns_source_data.get('spectra', [])
                        if len(spectra) == 0:
                            log(f"No spectra found on TNS for source {tns_source}")
                            continue

                        failed_spectra = []
                        failed_spectra_errors = []

                        for spectrum in spectra:
                            try:
                                data = read_tns_spectrum(spectrum, session)
                            except Exception as e:
                                log(
                                    f'Cannot read TNS spectrum {str(spectrum)}: {str(e)}'
                                )
                                continue
                            data["obj_id"] = tns_name
                            data["group_ids"] = [public_group_id]
                            post_spectrum(data, USER_ID, session)

                        if len(failed_spectra) > 0:
                            log(
                                f'Failed to retrieve {len(failed_spectra)}/{len(spectra)} TNS spectra from {tns_source}: {str(list(set(failed_spectra_errors)))}'
                            )
                        else:
                            log(
                                f'Successfully retrieved {len(spectra)} TNS spectra from {tns_source}'
                            )
        except Exception as e:
            log(f"Error processing TNS source {tns_source}: {e}")
            user_id = task.get("user_id", None)
            if user_id is not None:
                flow = Flow()
                if 'not found on TNS' in str(e):
                    flow.push(
                        user_id,
                        action_type="baselayer/SHOW_NOTIFICATION",
                        payload={
                            "note": str(e),
                            "type": "warning",
                        },
                    )
                else:
                    flow.push(
                        user_id,
                        action_type="baselayer/SHOW_NOTIFICATION",
                        payload={
                            "note": f"Error processing TNS source {tns_source}: {e}",
                            "type": "error",
                        },
                    )


def tns_watcher(queue):
    """Watch TNS for new sources and add them to the queue

    Parameters
    ----------
    queue : list
        The queue to add the TNS sources to, shared across threads
    """
    if (
        TNS_URL is None
        or bot_id is None
        or bot_name is None
        or api_key is None
        or look_back_days is None
    ):
        log("TNS watcher not configured, skipping")
        return
    tns_headers = {
        "User-Agent": f'tns_marker{{"tns_id": {bot_id},"type": "bot", "name": "{bot_name}"}}',
    }

    # when the service starts, we look back a certain number of days
    # useful if the app has been down for a while
    start_date = datetime.now() - timedelta(days=look_back_days)
    while True:
        # convert start date to isot format
        start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        tns_sources = get_recent_TNS(api_key, tns_headers, start_date, get_data=False)
        for tns_source in tns_sources:
            # add the tns_source to the queue
            queue.append(
                {
                    "tns_prefix": tns_source['prefix'],
                    "tns_name": tns_source['id'],
                    "obj_id": None,
                }
            )
            log(f"Added TNS source {tns_source['id']} to the queue for processing")

        # we always look at a minimum of 1 hour back in time
        start_date = datetime.now() - timedelta(hours=1)
        time.sleep(60 * 4)  # sleep for 4 minutes


def api(queue):
    """Start the internal API that endpoint that receives requests from the main app

    Parameters
    ----------
    queue : list
        The queue to add the sources to, shared across threads
    """

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

            required_keys = {'obj_id', 'user_id'}
            if not required_keys.issubset(set(data.keys())):
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"TNS requests requires keys {required_keys}",
                    }
                )

            queue.append(data)

            self.set_status(200)
            return self.write(
                {
                    "status": "success",
                    "message": "TNS request accepted into queue",
                    "data": {"queue_length": len(queue)},
                }
            )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.tns_retrieval_queue"])
    loop.run_forever()


if __name__ == "__main__":
    """Start the internal API, the TNS watcher, and the TNS retrieval service"""
    try:
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t3 = Thread(target=tns_watcher, args=(queue,))
        t.start()
        t2.start()
        t3.start()
        while True:
            log(f"Current TNS retrieval queue length: {len(queue)}")
            time.sleep(120)
    except Exception as e:
        log(f"Error starting TNS retrieval queue: {str(e)}")
        raise e
