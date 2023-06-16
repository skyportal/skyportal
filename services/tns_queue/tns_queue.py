import asyncio
import json
import time
import urllib
from threading import Thread

import astropy
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
from skyportal.handlers.api.photometry import serialize
from skyportal.models import DBSession, Instrument, Obj, Photometry, TNSRobot, User
from skyportal.utils.tns import (
    SNCOSMO_TO_TNSFILTER,
    TNS_INSTRUMENT_IDS,
    get_IAUname,
    get_tns_objects,
)
from skyportal.utils.calculations import great_circle_distance, radec_str2deg

env, cfg = load_env()
log = make_log('tns_queue')

init_db(**cfg['database'])

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')
search_frontend_url = urllib.parse.urljoin(TNS_URL, 'search')

bot_id = cfg.get('app.tns.bot_id', None)
bot_name = cfg.get('app.tns.bot_name', None)
api_key = cfg.get('app.tns.api_key', None)
look_back_days = cfg.get('app.tns.look_back_days', 1)

queue = []


def tns_submission(
    obj_ids,
    tnsrobot_id,
    user_id,
    reporters="",
    archival=False,
    archival_comment="",
    parent_session=None,
):
    """Submit objects to TNS.
    obj_ids : List[str]
        Object IDs
    tnsrobot_id : int
        TNSRobot ID
    user_id : int
        SkyPortal ID of User posting to TNS
    reporters : str
        Reporters to appear on TNS submission.
    archival : boolean
        Reporting the source as an archival source (i.e. no upperlimit).
    archival_comment : str
        Comment on archival source. Required if archival is True.
    parent_session : `sqlalchemy.orm.session.Session`
        Database session.
    """

    if parent_session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])
    else:
        session = parent_session

    user = session.scalar(sa.select(User).where(User.id == user_id))

    try:
        # for now we limit it to instruments and filters we have mapped to TNS
        instruments = session.scalars(
            Instrument.select(user).where(
                Instrument.name.in_(list(TNS_INSTRUMENT_IDS.keys()))
            )
        ).all()
        if len(instruments) == 0:
            raise ValueError(
                'No instrument with known IDs available. Submitting to TNS is only available for ZTF and DECam data (for now).'
            )

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

        if archival is True:
            if len(archival_comment) == 0:
                raise ValueError(
                    'If source flagged as archival, archival_comment is required'
                )

        tns_headers = {
            'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
        }

        for obj_id in obj_ids:
            obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()
            if obj is None:
                log(f'No object available with ID {obj_id}')
                continue

            photometry = session.scalars(
                Photometry.select(user).where(
                    Photometry.obj_id == obj_id,
                    Photometry.instrument_id.in_(
                        [instrument.id for instrument in instruments]
                    ),
                )
            ).all()

            if len(photometry) == 0:
                log(
                    f'No photometry from instrument that can be submitted to TNS) available for {obj_id}.'
                )
                continue

            photometry = [serialize(phot, 'ab', 'mag') for phot in photometry]

            _, tns_name = get_IAUname(altdata['api_key'], tns_headers, obj_id=obj_id)
            if tns_name is not None:
                log(f'{obj_id} already posted to TNS as {tns_name}.')
                continue

            time_first = mag_first = magerr_first = filt_first = instrument_first = None
            time_last = mag_last = magerr_last = filt_last = instrument_last = None
            time_last_nondetection = (
                limmag_last_nondetection
            ) = filt_last_nondetection = instrument_last_nondetection = None

            # split the photometry into detections and non-detections
            # non detections are those with mag=None
            detections, non_detections = [], []

            for phot in photometry:
                if phot['mag'] is None:
                    non_detections.append(phot)
                else:
                    detections.append(phot)

            if len(detections) == 0:
                log(f'Need at least one detection for TNS report of {obj_id}')
                continue

            if len(non_detections) == 0 and not archival:
                log(
                    f'Need at least one non-detection for non-archival TNS report of {obj_id}'
                )
                continue

            # sort each by mjd ascending
            non_detections = sorted(non_detections, key=lambda k: k['mjd'])
            detections = sorted(detections, key=lambda k: k['mjd'])

            time_first = detections[0]['mjd']
            mag_first = detections[0]['mag']
            magerr_first = detections[0]['magerr']
            filt_first = SNCOSMO_TO_TNSFILTER[detections[0]['filter']]
            instrument_first = TNS_INSTRUMENT_IDS[detections[0]['instrument_name']]

            time_last = detections[-1]['mjd']
            mag_last = detections[-1]['mag']
            magerr_last = detections[-1]['magerr']
            filt_last = SNCOSMO_TO_TNSFILTER[detections[-1]['filter']]
            instrument_last = TNS_INSTRUMENT_IDS[detections[-1]['instrument_name']]

            # find the the last non-detection that is before the first detection
            for phot in non_detections:
                if phot['mjd'] < time_first:
                    time_last_nondetection = phot['mjd']
                    limmag_last_nondetection = phot['limiting_mag']
                    filt_last_nondetection = SNCOSMO_TO_TNSFILTER[phot['filter']]
                    instrument_last_nondetection = TNS_INSTRUMENT_IDS[
                        phot['instrument_name']
                    ]

            if not archival:
                if time_last_nondetection is None:
                    log(
                        f'No non-detections found before first detection, cannot submit {obj_id} to TNS'
                    )
                    continue

            proprietary_period = {
                "proprietary_period_value": 0,
                "proprietary_period_units": "years",
            }
            if archival:
                non_detection = {"archiveid": "0", "archival_remarks": archival_comment}
            else:
                non_detection = {
                    "obsdate": astropy.time.Time(
                        time_last_nondetection, format='mjd'
                    ).jd,
                    "limiting_flux": limmag_last_nondetection,
                    "flux_units": "1",
                    "filter_value": filt_last_nondetection,
                    "instrument_value": instrument_last_nondetection,
                }
            phot_first = {
                "obsdate": astropy.time.Time(time_first, format='mjd').jd,
                "flux": mag_first,
                "flux_err": magerr_first,
                "flux_units": "1",
                "filter_value": filt_first,
                "instrument_value": instrument_first,
            }

            phot_last = {
                "obsdate": astropy.time.Time(time_last, format='mjd').jd,
                "flux": mag_last,
                "flux_err": magerr_last,
                "flux_units": "1",
                "filter_value": filt_last,
                "instrument_value": instrument_last,
            }

            at_report = {
                "ra": {"value": obj.ra},
                "dec": {"value": obj.dec},
                "groupid": tnsrobot.source_group_id,
                "internal_name_format": {
                    "prefix": instrument_first,
                    "year_format": "YY",
                    "postfix": "",
                },
                "internal_name": obj.id,
                "reporter": reporters,
                "discovery_datetime": astropy.time.Time(
                    time_first, format='mjd'
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f'),
                "at_type": 1,  # allow other options?
                "proprietary_period_groups": [tnsrobot.source_group_id],
                "proprietary_period": proprietary_period,
                "non_detection": non_detection,
                "photometry": {"photometry_group": {"0": phot_first, "1": phot_last}},
            }
            report = {"at_report": {"0": at_report}}

            data = {
                'api_key': altdata['api_key'],
                'data': json.dumps(report),
            }

            r = requests.post(report_url, headers=tns_headers, data=data)
            if r.status_code == 200:
                tns_id = r.json()['data']['report_id']
                log(f'Successfully submitted {obj_id} to TNS with request ID {tns_id}')
            else:
                log(f'Failed to submit {obj_id} to TNS: {r.content}')

    except Exception as e:
        log(f"Unable to generate TNS reports for {','.join(obj_ids)}: {e}")
    finally:
        if parent_session is None:
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

                obj_ids = data.get("obj_ids")
                tnsrobot_id = data.get("tnsrobot_id")
                user_id = data.get("user_id")
                reporters = data.get("reporters", "")
                archival = data.get("archival", False)
                archival_comment = data.get("archival_comment", "")

                tns_submission(
                    obj_ids,
                    tnsrobot_id,
                    user_id,
                    reporters=reporters,
                    archival=archival,
                    archival_comment=archival_comment,
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

            required_keys = {'obj_ids', 'tnsrobot_id', 'user_id', 'reporters'}
            if not required_keys.issubset(set(data.keys())):
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": "TNS requests require obj_ids, tnsrobot_id, user_id, and reporters",
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
    app.listen(cfg["ports.tns_queue"])
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
                            closest_obj = obj_query[0]
                            closest_obj_dist = great_circle_distance(
                                tns_ra, tns_dec, closest_obj.ra, closest_obj.dec
                            )
                            for obj in obj_query:
                                dist = great_circle_distance(
                                    tns_ra, tns_dec, obj.ra, obj.dec
                                )
                                if dist < closest_obj_dist:
                                    closest_obj = obj
                                    closest_obj_dist = dist
                            if obj.tns_name is None or obj.tns_name == "":
                                obj.tns_name = str(tns_obj["name"]).strip()
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
                        log(f"Error adding TNS name to object: {str(e)}")
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
            log(f"Current TNS queue length: {len(queue)}")
            time.sleep(120)
    except Exception as e:
        log(f"Error starting TNS queue: {str(e)}")
        raise e
