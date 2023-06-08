from astropy.time import Time
from datetime import datetime, timedelta
import json
import requests
import time

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.models import (
    DBSession,
    RecurringAPI,
    User,
    UserNotification,
)
from skyportal.tests import api

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('recurring_apis')

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
        if is_loaded():
            try:
                perform_api_calls()
            except Exception as e:
                log(e)
        time.sleep(30)


def perform_api_calls():
    now = datetime.utcnow()
    with DBSession() as session:
        try:
            user = session.query(User).where(User.id == 1).first()
            recurring_apis = session.scalars(
                RecurringAPI.select(user).where(
                    RecurringAPI.next_call <= now, RecurringAPI.active.is_(True)
                )
            ).all()
        except Exception as e:
            log(e)
            return

        for recurring_api in recurring_apis:
            token = recurring_api.owner.tokens[0].id
            if isinstance(recurring_api.payload, str):
                data = json.loads(recurring_api.payload)
            elif isinstance(recurring_api.payload, dict):
                data = recurring_api.payload
            else:
                raise Exception('payload must be dictionary or string')

            if recurring_api.method.upper() == "POST":
                response_status, data = api(
                    recurring_api.method.upper(),
                    recurring_api.endpoint,
                    token=token,
                    host=host,
                    data=data,
                )
            elif recurring_api.method.upper() == "GET":
                response_status, data = api(
                    recurring_api.method.upper(),
                    recurring_api.endpoint,
                    token=token,
                    host=host,
                    params=data,
                )
            else:
                log('Unable to execute recurring API calls that are not GET or POST')
                continue

            while True:
                recurring_api.next_call += timedelta(days=recurring_api.call_delay)
                if recurring_api.next_call > Time(now, format='datetime'):
                    break

            if response_status == 200:
                recurring_api.number_of_retries = MAX_RETRIES
                text_to_send = f'Successfully called recurring API {recurring_api.id}'
            else:
                recurring_api.number_of_retries = recurring_api.number_of_retries - 1
                if recurring_api.number_of_retries == 0:
                    recurring_api.active = False
                    text_to_send = f'Failed call to recurring API {recurring_api.id}: {str(data)}; Maximum Retries exceeded, deactivating service.'
                else:
                    text_to_send = f'Failed call to recurring API {recurring_api.id}: {str(data)}; will try again {recurring_api.next_call}, remaining calls before deactivation: {recurring_api.number_of_retries}.'

            log(text_to_send)
            session.add(recurring_api)
            session.add(
                UserNotification(
                    user=recurring_api.owner,
                    text=text_to_send,
                    notification_type="Recurring API",
                )
            )
            session.commit()


if __name__ == "__main__":
    service()
