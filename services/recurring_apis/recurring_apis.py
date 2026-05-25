import json
import time
import traceback
from datetime import UTC, datetime, timedelta, timezone

from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import DBSession, RecurringAPI, User, UserNotification
from skyportal.tests import api
from skyportal.utils.services import HOST, check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("recurring_apis")

MAX_SLEEP = cfg.get("misc", {}).get("max_seconds_to_sleep_recurring_apis_service", 60)
MAX_RETRIES = 10


def _claim_due_api(session, user, now):
    """Claim one due recurring API for processing.

    Returns the row with a row-level lock held for the current transaction, so
    other replicas calling this concurrently will skip it.
    """
    return session.scalars(
        RecurringAPI.select(user)
        .where(RecurringAPI.next_call <= now, RecurringAPI.active.is_(True))
        .with_for_update(skip_locked=True)
        .limit(1)
    ).first()


def _process_recurring_api(recurring_api, now):
    """Execute the API call and mutate ``recurring_api`` with the outcome."""
    token = recurring_api.owner.tokens[0].id
    if isinstance(recurring_api.payload, str):
        data = json.loads(recurring_api.payload)
    elif isinstance(recurring_api.payload, dict):
        data = recurring_api.payload
    else:
        raise Exception("payload must be dictionary or string")

    method = recurring_api.method.upper()
    if method == "POST":
        response_status, response_data = api(
            method,
            recurring_api.endpoint,
            token=token,
            host=HOST,
            data=data,
        )
    elif method == "GET":
        response_status, response_data = api(
            method,
            recurring_api.endpoint,
            token=token,
            host=HOST,
            params=data,
        )
    else:
        log("Unable to execute recurring API calls that are not GET or POST")
        return None

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
            text_to_send = (
                f"Failed call to recurring API {recurring_api.id}: "
                f"{str(response_data)}; Maximum Retries exceeded, deactivating "
                f"service."
            )
        else:
            text_to_send = (
                f"Failed call to recurring API {recurring_api.id}: "
                f"{str(response_data)}; will try again {recurring_api.next_call}, "
                f"remaining calls before deactivation: "
                f"{recurring_api.number_of_retries}."
            )

    log(text_to_send)
    return text_to_send


def perform_api_calls():
    sleep_time = MAX_SLEEP
    now = datetime.now(UTC).replace(tzinfo=None)

    # Drain due rows one at a time. Each row is claimed via FOR UPDATE SKIP
    # LOCKED, so concurrent replicas get disjoint rows. The HTTP call runs
    # inside the transaction holding the row lock -- fine because the lock is
    # per-row, not service-wide, so other replicas can process other rows in
    # parallel.
    while True:
        with DBSession() as session:
            user = session.query(User).where(User.id == 1).first()
            recurring_api = _claim_due_api(session, user, now)
            if recurring_api is None:
                break

            try:
                text_to_send = _process_recurring_api(recurring_api, now)
                if text_to_send is not None:
                    session.add(recurring_api)
                    session.add(
                        UserNotification(
                            user=recurring_api.owner,
                            text=text_to_send,
                            notification_type="Recurring API",
                        )
                    )
                session.commit()
            except Exception as e:
                log(e)
                traceback.print_exc()
                session.rollback()

    # Determine sleep target. No lock needed -- this is a read.
    with DBSession() as session:
        user = session.query(User).where(User.id == 1).first()
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
            dt = (next_recurring_api.next_call - now).total_seconds()
            sleep_time = min(sleep_time, dt)

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
