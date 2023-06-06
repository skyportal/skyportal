import time
from datetime import datetime, timedelta

import requests
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.alert import (
    alert_available,
    get_alerts_by_position,
    post_alert,
)
from skyportal.models import DBSession, Listing, Telescope, User

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('watchlist')

REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']
MAX_RETRIES = 10


host = f'{cfg["server.protocol"]}://{cfg["server.host"]}' + (
    f':{cfg["server.port"]}' if cfg['server.port'] not in [80, 443] else ''
)


def is_loaded():
    try:
        r = requests.get(f'{host}/api/sysinfo', timeout=REQUEST_TIMEOUT_SECONDS)
    except:  # noqa: E722
        status_code = 0
    else:
        status_code = r.status_code

    if status_code == 200:
        return True
    else:
        return False


def ztf_observing_times():
    with DBSession() as session:
        telescope = (
            session.query(Telescope)
            .where(Telescope.nickname.in_(['ZTF', 'P48']))
            .first()
        )
        if telescope is None:
            raise Exception('Could not find ZTF')
        time_info = telescope.current_time
        return time_info


def service():
    while True:
        loaded = is_loaded()
        time_info = None
        if loaded and alert_available:
            try:
                time_info = ztf_observing_times()
            except Exception as e:
                log(e)
                time.sleep(5)
                continue
            try:
                check_watch_list(time_info)
            except Exception as e:
                log(e)
                time.sleep(5)
        else:
            time.sleep(60)


def check_watch_list(time_info):
    shortest_interval = 60
    start = time.time()
    with DBSession() as session:
        try:
            user = session.query(User).where(User.id == 1).first()
            listings = session.scalars(
                Listing.select(user).where(Listing.list_name == "watchlist")
            ).all()
        except Exception as e:
            log(e)
            return

        listing_ids = [listing.id for listing in listings]
        # we get the list of cadences for each listing that needs to run during processing time, as those are the critical ones
        cadences = [
            listing.params.get("cadence", 1440.0)
            for listing in listings
            if listing.params is not None
            and listing.params.get("after_night", True) is False
        ]
        shortest_interval = (
            min(cadences if len(cadences) > 0 else [1]) * 60.0
        )  # in seconds, defaults to 60 seconds if no cadences are found
        for listing_id in listing_ids:
            try:
                listing = session.query(Listing).where(Listing.id == listing_id).first()
                owner_id = listing.user_id
                owner = session.query(User).where(User.id == owner_id).first()
                obj = listing.obj
                group_ids = [g.id for g in owner.groups]

                params = listing.params if listing.params is not None else {}
                params = {
                    "arcsec": params.get(
                        "arcsec", 5.0
                    ),  # arcseconds to use for the cone search radius
                    "cadence": params.get(
                        "cadence", 1440.0
                    ),  # how often to check for new candidates around that location in minutes
                    "after_night": params.get(
                        "after_night", True
                    ),  # whether to only check for new candidates after the end of the night
                    "filter": params.get(
                        "filter", {}
                    ),  # extra kowalski filters to apply when querying for new candidates
                    "last_processed_at": params.get(
                        "last_processed_at", obj.created_at.isoformat()
                    ),  # when was the last time we checked for new candidates
                    "last_got_candidates_at": params.get(
                        "last_got_candidates_at", obj.created_at.isoformat()
                    ),  # when was the last time we got candidates
                }

                last_got_candidates_at = Time(
                    params["last_got_candidates_at"], format='isot', scale='utc'
                ).jd

                # if after_night is True, force the cadence to one day as anyway nothing is updated during the day
                if params["after_night"]:
                    params["cadence"] = 1440.0

                if params["after_night"] and time_info['is_night_astronomical']:
                    # if the user requests for update after night has ended and its still night, skip
                    continue
                if (
                    Time(
                        params["last_processed_at"], format='isot', scale='utc'
                    ).datetime
                    + timedelta(minutes=params["cadence"])
                    > datetime.utcnow()
                ):
                    continue

                # we will also update it once we get the alerts, but we update it here in case we get any errors below
                # to avoid getting stuck in a loop
                listing.params = {
                    **params,
                    "last_processed_at": datetime.utcnow().isoformat(),
                }
                session.commit()

                # allow access to public data only by default
                program_id_selector = {1}

                for stream in owner.streams:
                    if "ztf" in stream.name.lower():
                        program_id_selector.update(
                            set(stream.altdata.get("selector", []))
                        )

                program_id_selector = list(program_id_selector)

                # we constrain the query to only return alerts that were created after the last time we got candidates
                filter = {
                    **params["filter"],
                    "candidate.jd": {
                        "$gte": last_got_candidates_at,
                    },
                }

                projection = {
                    "_id": 0,
                    "objectId": 1,
                    "candidate.jd": 1,
                }

                alerts = get_alerts_by_position(
                    obj.ra,
                    obj.dec,
                    params["arcsec"],
                    "arcsec",
                    program_id_selector,
                    projection=projection,
                    include_all_fields=False,
                    filter=filter,
                )

                if alerts is None:
                    continue

                object_ids = list({alert['objectId'] for alert in alerts})
                jds = [alert['candidate']['jd'] for alert in alerts]

                if len(object_ids) == 0:
                    continue

                # we update the last_got_candidates_at to the latest jd of the alerts we just got
                # this is to avoid missing alerts as there is a delay between when the alert is created and when it is available for query
                # so if we get alerts with jd < last_processed_at ingested in Kowalski after last_processed_at, we will miss them

                listing.params = {
                    **params,
                    "last_got_candidates_at": Time(max(jds), format='jd').isot,
                }

                all_photometry_ids = []
                for object_id in object_ids:
                    photometry_ids, _ = post_alert(
                        object_id,
                        group_ids,
                        owner_id,
                        session,
                        program_id_selector=program_id_selector,
                    )
                    if len(photometry_ids) > 0:
                        all_photometry_ids.extend(photometry_ids)

                if len(all_photometry_ids) > 0:
                    request_body = {
                        'target_class_name': "Listing",
                        'target_id': listing_id,
                    }

                    notifications_microservice_url = (
                        f'http://127.0.0.1:{cfg["ports.notification_queue"]}'
                    )

                    resp = requests.post(
                        notifications_microservice_url,
                        json=request_body,
                        timeout=30,
                    )
                    if resp.status_code != 200:
                        log(
                            f'Notification request failed for {request_body["target_class_name"]} with ID {request_body["target_id"]}: {resp.content}'
                        )
            except Exception as e:
                log(e)
                DBSession.rollback()
                continue
    end = time.time()
    # if we took less than the shortest interval, sleep for the difference. Otherwise, don't sleep
    if end - start < shortest_interval:
        time.sleep(shortest_interval - (end - start))


if __name__ == "__main__":
    service()
