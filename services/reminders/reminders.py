# For Michael, an example test run with Curl:
#
# curl -X POST http://localhost:64510 -d '{"method": "GET", "endpoint": "http://localhost:9980"}'
#

from astropy.time import Time
from datetime import datetime, timedelta
import requests

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from skyportal.models import (
    DBSession,
    Reminder,
    ReminderOnSpectrum,
    ReminderOnGCN,
    ReminderOnShift,
    UserNotification,
)
from skyportal.models.gcn import GcnEvent
from skyportal.models.shift import Shift
import time

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('reminders')

REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']


def service():
    loaded = False
    while not loaded:
        # ping the app to see if its running
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
            loaded = True
    while loaded:
        try:
            send_reminders()
        except Exception as e:
            log(e)


def send_reminders():
    now = datetime.utcnow()
    reminders = []
    with DBSession() as session:
        try:
            reminders = (
                (
                    session.query(Reminder)
                    .where(Reminder.number_of_reminders > 0)
                    .where(Reminder.next_reminder <= now)
                    .all()
                )
                + (
                    session.query(ReminderOnSpectrum)
                    .where(ReminderOnSpectrum.number_of_reminders > 0)
                    .where(ReminderOnSpectrum.next_reminder <= now)
                    .all()
                )
                + (
                    session.query(ReminderOnGCN)
                    .where(ReminderOnGCN.number_of_reminders > 0)
                    .where(ReminderOnGCN.next_reminder <= now)
                    .all()
                )
                + (
                    session.query(ReminderOnShift)
                    .where(ReminderOnShift.number_of_reminders > 0)
                    .where(ReminderOnShift.next_reminder <= now)
                    .all()
                )
            )
        except Exception as e:
            log(e)

        ws_flow = Flow()
        for reminder in reminders:
            reminder_type = reminder.__class__
            if reminder_type == Reminder:
                text_to_send = (
                    f"Reminder of source *{reminder.obj_id}*: {reminder.text}"
                )
                url_endpoint = f"/source/{reminder.obj_id}"
            elif reminder_type == ReminderOnSpectrum:
                text_to_send = (
                    f"Reminder of spectrum *{reminder.spectrum_id}*: {reminder.text}"
                )
                url_endpoint = f"/source/{reminder.spectrum_id}"
            elif reminder_type == ReminderOnGCN:
                gcn_event = session.query(GcnEvent).get(reminder.gcn_id)
                text_to_send = (
                    f"Reminder of GCN event *{gcn_event.dateobs}*: {reminder.text}"
                )
                url_endpoint = f"/gcn_events/{reminder.gcn_id}"
            elif reminder_type == ReminderOnShift:
                shift = session.query(Shift).get(reminder.shift_id)
                text_to_send = f"Reminder of shift *{shift.name}*: {reminder.text}"
                url_endpoint = f"/shifts/{shift.id}"

            session.add(
                UserNotification(
                    user=reminder.user,
                    text=text_to_send,
                    notification_type="mention",
                    url=url_endpoint,
                )
            )
            loop = True
            while loop:
                reminder.number_of_reminders = reminder.number_of_reminders - 1
                reminder.next_reminder = reminder.next_reminder + timedelta(
                    days=reminder.reminder_delay
                )
                if reminder.next_reminder > Time(now, format='datetime'):
                    loop = False
            session.add(reminder)
            session.commit()

            ws_flow.push(reminder.user.id, "skyportal/FETCH_NOTIFICATIONS")

    time.sleep(5)


if __name__ == "__main__":
    service()
