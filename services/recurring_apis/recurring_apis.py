import json
import time
from datetime import datetime, timedelta, timezone

from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    RecurringAPI,
    User,
    UserNotification,
)
from skyportal.tests import api
from skyportal.utils.services import HOST, check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("recurring_apis")

MAX_RETRIES = 10


def perform_api_calls():
    sleep_time = 60
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
                raise Exception("payload must be dictionary or string")

            if recurring_api.method.upper() == "POST":
                response_status, data = api(
                    recurring_api.method.upper(),
                    recurring_api.endpoint,
                    token=token,
                    host=HOST,
                    data=data,
                )
            elif recurring_api.method.upper() == "GET":
                response_status, data = api(
                    recurring_api.method.upper(),
                    recurring_api.endpoint,
                    token=token,
                    host=HOST,
                    params=data,
                )
            else:
                log("Unable to execute recurring API calls that are not GET or POST")
                continue

            while True:
                recurring_api.next_call += timedelta(days=recurring_api.call_delay)
                if recurring_api.next_call > Time(now, format="datetime"):
                    break

            if response_status == 200:
                recurring_api.number_of_retries = MAX_RETRIES
                text_to_send = f"Successfully called recurring API {recurring_api.id}"
            else:
                recurring_api.number_of_retries = recurring_api.number_of_retries - 1
                if recurring_api.number_of_retries == 0:
                    recurring_api.active = False
                    text_to_send = f"Failed call to recurring API {recurring_api.id}: {str(data)}; Maximum Retries exceeded, deactivating service."
                else:
                    text_to_send = f"Failed call to recurring API {recurring_api.id}: {str(data)}; will try again {recurring_api.next_call}, remaining calls before deactivation: {recurring_api.number_of_retries}."

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

        next_recurring_api = session.scalars(
            RecurringAPI.select(user)
            .where(
                RecurringAPI.next_call > now,
                RecurringAPI.next_call <= now + timedelta(seconds=sleep_time),
                RecurringAPI.active.is_(True),
            )
            .order_by(RecurringAPI.next_call)
            .limit(1)
        ).first()
        if next_recurring_api is not None:
            dt = (
                next_recurring_api.next_call
                - datetime.now(timezone.utc).replace(tzinfo=None)
            ).total_seconds()
            if dt < 0:
                dt = 0
            elif dt < sleep_time:
                sleep_time = dt

    if sleep_time > 0:
        time.sleep(sleep_time)


@check_loaded(logger=log)
def service(*args, **kwargs):
    while True:
        try:
            perform_api_calls()
        except Exception as e:
            log(e)


if __name__ == "__main__":
    service()
