import asyncio
import json
import time
import urllib
import traceback
from threading import Thread

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
from skyportal.models import DBSession, Obj, TNSRobot, User, Group
from skyportal.utils.tns import (
    get_IAUname,
    read_tns_photometry,
    read_tns_spectrum,
    get_recent_TNS,
    get_tns_objects,
)
from skyportal.utils.calculations import radec_str2deg

env, cfg = load_env()
log = make_log('tns_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
object_url = urllib.parse.urljoin(TNS_URL, 'api/get/object')
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')

bot_id = cfg.get('app.tns.bot_id', None)
bot_name = cfg.get('app.tns.bot_name', None)
api_key = cfg.get('app.tns.api_key', None)
look_back_days = cfg.get('app.tns.look_back_days', 1)

queue = []


def tns_bulk_retrieval(
    start_date,
    tnsrobot_id,
    user_id,
    group_ids=None,
    include_photometry=False,
    include_spectra=False,
    parent_session=None,
):
    """Retrieve objects from TNS.
    start_date : str
        ISO-based start time
    tnsrobot_id : int
        TNSRobot ID
    user_id : int
        SkyPortal ID of User retrieving from TNS
    group_ids : List[int]
        List of groups to post TNS sources to
    include_photometry: boolean
        Include photometry available on TNS
    include_spectra : boolean
        Include spectra available on TNS
    """

    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    user = session.scalar(sa.select(User).where(User.id == user_id))
    if group_ids is None:
        public_group = session.scalar(
            sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
        )
        if public_group is None:
            raise ValueError(
                f'No group(s) specified, and could not find public group {cfg["misc.public_group_name"]}'
            )
        group_ids = [public_group.id]

    try:
        tnsrobot = session.scalars(
            TNSRobot.select(user).where(TNSRobot.id == tnsrobot_id)
        ).first()
        if tnsrobot is None:
            raise ValueError(f'No TNSRobot available with ID {tnsrobot_id}')

        altdata = tnsrobot.altdata
        if not altdata:
            raise ValueError('Missing TNS information.')
        if 'api_key' not in altdata:
            raise ValueError('Missing TNS API key.')

        tns_headers = {
            'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
        }

        tns_sources = get_recent_TNS(
            altdata['api_key'], tns_headers, start_date, get_data=False
        )
        if len(tns_sources) == 0:
            raise ValueError(f'No objects posted to TNS since {start_date}.')

        for source in tns_sources:
            s = session.scalars(Obj.select(user).where(Obj.id == source['id'])).first()
            if s is None:
                log(f"Posting {source['id']} as source")
                data = {
                    'api_key': api_key,
                    'data': json.dumps(
                        {
                            "objname": source["id"],
                        }
                    ),
                }

                r = requests.post(
                    object_url,
                    headers=tns_headers,
                    data=data,
                    allow_redirects=True,
                    stream=True,
                    timeout=10,
                )

                count = 0
                count_limit = 5
                while r.status_code == 429 and count < count_limit:
                    log(
                        f'TNS request rate limited: {str(r.json())}.  Waiting 30 seconds to try again.'
                    )
                    time.sleep(30)
                    r = requests.post(object_url, headers=tns_headers, data=data)
                    count += 1

                if count == count_limit:
                    log(f"TNS request rate limited. Skipping {source['id']}.")
                    continue

                if r.status_code == 200:
                    source_data = r.json().get("data", dict()).get("reply", dict())
                    if source_data:
                        source["ra"] = source_data.get("radeg", None)
                        source["dec"] = source_data.get("decdeg", None)

                source['group_ids'] = group_ids
                post_source(source, user_id, session)

            tns_retrieval(
                source['id'],
                tnsrobot_id,
                user_id,
                group_ids=group_ids,
                include_photometry=include_photometry,
                include_spectra=include_spectra,
                parent_session=session,
            )
        session.commit()

    except Exception as e:
        log(f"Unable to retrieve TNS report for objects since {start_date}: {e}")
    finally:
        if parent_session is not None:
            session.close()
            Session.remove()


def tns_retrieval(
    obj_id,
    tnsrobot_id,
    user_id,
    group_ids=None,
    include_photometry=False,
    include_spectra=False,
    radius=2.0,
    parent_session=None,
):
    """Retrieve object from TNS.
    obj_id : str
        Object ID
    tnsrobot_id : int
        TNSRobot ID
    user_id : int
        SkyPortal ID of User retrieving from TNS
    include_photometry: boolean
        Include photometry available on TNS
    include_spectra : boolean
        Include spectra available on TNS
    group_ids : List[int]
        List of groups to share photometry and spectroscopy with
    """

    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    flow = Flow()

    user = session.scalar(sa.select(User).where(User.id == user_id))
    if group_ids is None:
        group_ids = [g.id for g in user.accessible_groups]

    try:
        obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()
        if obj is None:
            raise ValueError(f'No object available with ID {obj_id}')

        tnsrobot = session.scalars(
            TNSRobot.select(user).where(TNSRobot.id == tnsrobot_id)
        ).first()
        if tnsrobot is None:
            raise ValueError(f'No TNSRobot available with ID {tnsrobot_id}')

        altdata = tnsrobot.altdata
        if not altdata:
            raise ValueError('Missing TNS information.')
        if 'api_key' not in altdata:
            raise ValueError('Missing TNS API key.')

        tns_headers = {
            'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
        }

        tns_prefix, tns_name = get_IAUname(
            altdata['api_key'],
            tns_headers,
            ra=obj.ra,
            dec=obj.dec,
            radius=float(radius),
        )
        if tns_name is None:
            raise ValueError(f'{obj_id} not yet posted to TNS.')

        obj.tns_name = f"{tns_prefix} {tns_name}"

        data = {
            'api_key': altdata['api_key'],
            'data': json.dumps(
                {
                    "objname": tns_name,
                    "photometry": "1" if include_photometry else "0",
                    "spectra": "1" if include_spectra else "0",
                }
            ),
        }

        r = requests.post(
            object_url,
            headers=tns_headers,
            data=data,
            allow_redirects=True,
            stream=True,
            timeout=10,
        )

        count = 0
        count_limit = 5
        while r.status_code == 429 and count < count_limit:
            log(
                f'TNS request rate limited: {str(r.json())}.  Waiting 30 seconds to try again.'
            )
            time.sleep(30)
            r = requests.post(
                object_url,
                headers=tns_headers,
                data=data,
                allow_redirects=True,
                stream=True,
                timeout=10,
            )
            count += 1

        if r.status_code == 200:
            source_data = r.json().get("data", dict()).get("reply", dict())
            if source_data:
                obj.tns_info = source_data
                if include_photometry and 'photometry' in source_data:
                    photometry = source_data['photometry']

                    failed_photometry = []
                    failed_photometry_errors = []
                    for phot in photometry:
                        read_photometry = False
                        try:
                            df, instrument_id = read_tns_photometry(phot, session)
                            data_out = {
                                'obj_id': obj_id,
                                'instrument_id': instrument_id,
                                'group_ids': group_ids,
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
                            f'Failed to retrieve {len(failed_photometry)}/{len(photometry)} TNS photometry points for {obj_id} from TNS as {tns_name}: {str(list(set(failed_photometry_errors)))}'
                        )
                    else:
                        log(
                            f'Successfully retrieved {len(photometry)} TNS photometry points for {obj_id} from TNS as {tns_name}'
                        )

                if include_spectra and 'spectra' in source_data:
                    group_ids = [g.id for g in user.accessible_groups]
                    spectra = source_data['spectra']

                    failed_spectra = []
                    failed_spectra_errors = []

                    for spectrum in spectra:
                        try:
                            data = read_tns_spectrum(spectrum, session)
                        except Exception as e:
                            log(f'Cannot read TNS spectrum {str(spectrum)}: {str(e)}')
                            continue
                        data["obj_id"] = obj_id
                        data["group_ids"] = group_ids
                        post_spectrum(data, user_id, session)

                    if len(failed_spectra) > 0:
                        log(
                            f'Failed to retrieve {len(failed_spectra)}/{len(spectra)} TNS spectra for {obj_id} from TNS as {tns_name}: {str(list(set(failed_spectra_errors)))}'
                        )
                    else:
                        log(
                            f'Successfully retrieved {len(spectra)} TNS spectra for {obj_id} from TNS as {tns_name}'
                        )

            log(f'Successfully retrieved {obj_id} from TNS as {tns_name}')
        else:
            log(f'Failed to retrieve {obj_id} from TNS: {r.content}')
        session.commit()

        flow.push(
            '*',
            'skyportal/REFRESH_SOURCE',
            payload={'obj_key': obj.internal_key},
        )

    except Exception as e:
        traceback.print_exc()
        log(f"Unable to retrieve TNS report for {obj_id}: {e}")
        try:
            flow.push(
                user.id,
                'baselayer/SHOW_NOTIFICATION',
                {
                    'note': f'Unable to retrieve TNS report for {obj_id}: {e}',
                    'type': 'error',
                },
            )
        except Exception:
            pass
    finally:
        if parent_session is not None:
            session.close()
            Session.remove()


def service(queue):
    while True:
        with DBSession() as session:
            try:
                if len(queue) == 0:
                    time.sleep(1)
                    continue
                data = queue.pop(0)
                if data is None:
                    continue

                tnsrobot_id = data.get("tnsrobot_id")
                user_id = data.get("user_id")
                include_photometry = data.get("include_photometry", False)
                include_spectra = data.get("include_spectra", False)
                group_ids = data.get("group_ids", None)
                obj_id = data.get("obj_id", None)
                start_date = data.get("start_date", None)
                radius = data.get("radius", None)

                if obj_id is None and start_date is None:
                    raise ValueError('obj_id or start_date must be specified')

                if obj_id is not None:
                    tns_retrieval(
                        obj_id,
                        tnsrobot_id,
                        user_id,
                        group_ids=group_ids,
                        include_photometry=include_photometry,
                        include_spectra=include_spectra,
                        radius=radius,
                        parent_session=session,
                    )

                if start_date is not None:
                    tns_bulk_retrieval(
                        start_date,
                        tnsrobot_id,
                        user_id,
                        group_ids=group_ids,
                        include_photometry=include_photometry,
                        include_spectra=include_spectra,
                        parent_session=session,
                    )
            except Exception as e:
                log(
                    f"Error processing TNS request for objects {str(data['obj_ids'])}: {str(e)}"
                )


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

            required_keys = {'tnsrobot_id', 'user_id'}
            if not required_keys.issubset(set(data.keys())):
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": "TNS requests require tnsrobot_id and user_id",
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


def tns_watcher():
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

    flow = Flow()

    while True:
        try:
            tns_objects = get_tns_objects(
                tns_headers,
                discovered_period_value=look_back_days,
                discovered_period_units='days',
            )
            if len(tns_objects) > 0:
                for tns_obj in tns_objects:
                    tns_ra, tns_dec = radec_str2deg(tns_obj["ra"], tns_obj["dec"])
                    if Session.registry.has():
                        session = Session()
                    else:
                        session = Session(bind=DBSession.session_factory.kw["bind"])
                    try:
                        other = ca.Point(ra=tns_ra, dec=tns_dec)
                        obj_query = session.scalars(
                            sa.select(Obj).where(
                                Obj.within(other, 0.000555556)  # 2 arcseconds
                            )
                        ).all()
                        if len(obj_query) > 0:
                            for obj in obj_query:
                                try:
                                    if obj.tns_name == str(tns_obj["name"]).strip():
                                        continue
                                    elif obj.tns_name is None or obj.tns_name == "":
                                        obj.tns_name = str(tns_obj["name"]).strip()
                                    # if the current name doesn't have the SN designation but the new name has it, update
                                    elif not str(
                                        obj.tns_name
                                    ).lower().strip().startswith(
                                        "sn"
                                    ) and "AT" not in str(
                                        tns_obj["name"]
                                    ):
                                        obj.tns_name = str(tns_obj["name"]).strip()
                                    else:
                                        continue

                                    session.commit()
                                    log(
                                        f"Updated object {obj.id} with TNS name {tns_obj['name']}"
                                    )
                                    flow.push(
                                        '*',
                                        'skyportal/REFRESH_SOURCE',
                                        payload={'obj_key': obj.internal_key},
                                    )
                                except Exception as e:
                                    log(f"Error updating object: {str(e)}")
                                    session.rollback()
                    except Exception as e:
                        log(f"Error adding TNS name to objects: {str(e)}")
                        session.rollback()
                    finally:
                        session.close()
        except Exception as e:
            log(f"Error getting TNS objects: {str(e)}")
        time.sleep(60 * 4)


if __name__ == "__main__":
    try:
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t3 = Thread(target=tns_watcher)
        t.start()
        t2.start()
        t3.start()

        while True:
            log(f"Current TNS retrieval queue length: {len(queue)}")
            time.sleep(120)
    except Exception as e:
        log(f"Error starting TNS retrieval queue: {str(e)}")
        raise e
