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
)
from skyportal.tests import api

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('recurring_apis')

REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']


def is_loaded():
    port = cfg['ports.app_internal']
    try:
        r = requests.get(
            f'http://localhost:{port}/api/sysinfo', timeout=REQUEST_TIMEOUT_SECONDS
        )
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
        time.sleep(5)


def perform_api_calls():
    now = datetime.utcnow()
    with DBSession() as session:
        try:
            user = session.query(User).get(1)
            recurring_apis = session.scalars(
                RecurringAPI.select(user).where(RecurringAPI.next_call <= now)
            ).all()
        except Exception as e:
            log(e)
            return

        for recurring_api in recurring_apis:
            token = recurring_api.owner.tokens[0].id
            host = (
                f'{cfg["server.protocol"]}://{cfg["server.host"]}:{cfg["server.port"]}'
            )
            if isinstance(recurring_api.payload, str):
                data = json.loads(recurring_api.payload)
            elif isinstance(recurring_api.payload, dict):
                data = recurring_api.payload
            else:
                raise Exception('payload must be dictionary or string')

            response_status, data = api(
                recurring_api.method.upper(),
                recurring_api.endpoint,
                token=token,
                host=host,
                data=data,
            )
            if response_status == 200:
                while True:
                    recurring_api.next_call += timedelta(days=recurring_api.call_delay)
                    if recurring_api.next_call > Time(now, format='datetime'):
                        break
                session.add(recurring_api)
                session.commit()

                log(f'Successfully called recurring API {recurring_api.id}')
            else:
                log(f'Failed call to recurring API {recurring_api.id}: {str(data)}')


if __name__ == "__main__":
    service()
