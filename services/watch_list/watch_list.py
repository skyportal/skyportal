import requests

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.models import (
    DBSession,
    Listing,
    User,
)
from skyportal.handlers.api.alert import (
    post_alert,
    get_alerts_by_position,
    alert_available,
)

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


def service():
    while True:
        if is_loaded() and alert_available:
            try:
                check_watch_list()
            except Exception as e:
                log(e)


def check_watch_list():
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
        for listing_id in listing_ids:
            listing = session.query(Listing).where(Listing.id == listing_id).first()
            owner_id = listing.user_id
            owner = session.query(User).where(User.id == owner_id).first()
            obj = listing.obj
            group_ids = [g.id for g in owner.groups]

            # allow access to public data only by default
            program_id_selector = {1}

            for stream in owner.streams:
                if "ztf" in stream.name.lower():
                    program_id_selector.update(set(stream.altdata.get("selector", [])))

            program_id_selector = list(program_id_selector)

            projection = {
                "_id": 0,
                "objectId": 1,
            }
            alerts = get_alerts_by_position(
                obj.ra,
                obj.dec,
                2.0,  # arcseconds
                "arcsec",
                program_id_selector,
                projection=projection,
                include_all_fields=True,
            )
            object_ids = {alert['objectId'] for alert in alerts}
            for object_id in object_ids:
                photometry_ids, _ = post_alert(
                    object_id,
                    group_ids,
                    owner_id,
                    session,
                    program_id_selector=program_id_selector,
                )
                if len(photometry_ids) > 0:
                    request_body = {
                        'target_class_name': "Listing",
                        'target_id': listing_id,
                    }

                    notifications_microservice_url = (
                        f'http://127.0.0.1:{cfg["ports.notification_queue"]}'
                    )

                    resp = requests.post(
                        notifications_microservice_url, json=request_body, timeout=30
                    )
                    if resp.status_code != 200:
                        log(
                            f'Notification request failed for {request_body["target_class_name"]} with ID {request_body["target_id"]}: {resp.content}'
                        )


if __name__ == "__main__":
    service()
