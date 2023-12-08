from astropy.time import Time
from datetime import datetime, timedelta
import requests

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from skyportal.models import (
    ThreadSession,
    Reminder,
    ReminderOnSpectrum,
    ReminderOnGCN,
    ReminderOnShift,
    UserNotification,
)
from skyportal.models.gcn import GcnEvent
from skyportal.models.shift import Shift
from baselayer.app.models import User
import time

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('reminders')

REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']

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
                send_reminders()
            except Exception as e:
                log(e)
        time.sleep(60)


def send_reminders():
    now = datetime.utcnow()
    reminders = []
    with ThreadSession() as session:
        try:
            user = session.query(User).where(User.id == 1).first()
            reminders = (
                (
                    session.scalars(
                        Reminder.select(user)
                        .where(Reminder.number_of_reminders > 0)
                        .where(Reminder.next_reminder <= now)
                    ).all()
                )
                + (
                    session.scalars(
                        ReminderOnSpectrum.select(user)
                        .where(ReminderOnSpectrum.number_of_reminders > 0)
                        .where(ReminderOnSpectrum.next_reminder <= now)
                    ).all()
                )
                + (
                    session.scalars(
                        ReminderOnGCN.select(user)
                        .where(ReminderOnGCN.number_of_reminders > 0)
                        .where(ReminderOnGCN.next_reminder <= now)
                    ).all()
                )
                + (
                    session.scalars(
                        ReminderOnShift.select(user)
                        .where(ReminderOnShift.number_of_reminders > 0)
                        .where(ReminderOnShift.next_reminder <= now)
                    ).all()
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
                notification_type = "reminder_on_source"
            elif reminder_type == ReminderOnSpectrum:
                text_to_send = f"Reminder of spectrum *{reminder.spectrum_id}* on source *{reminder.obj_id}*: {reminder.text}"
                url_endpoint = f"/source/{reminder.obj_id}"
                notification_type = "reminder_on_spectra"
            elif reminder_type == ReminderOnGCN:
                gcn_event = session.scalars(
                    GcnEvent.select(user).where(GcnEvent.id == reminder.gcn_id)
                ).first()
                text_to_send = (
                    f"Reminder of GCN event *{gcn_event.dateobs}*: {reminder.text}"
                )
                url_endpoint = f"/gcn_events/{reminder.gcn_id}"
                notification_type = "reminder_on_gcn"
            elif reminder_type == ReminderOnShift:
                shift = session.scalars(
                    Shift.select(user).where(Shift.id == reminder.shift_id)
                ).first()
                text_to_send = f"Reminder of shift *{shift.name}*: {reminder.text}"
                url_endpoint = f"/shifts/{shift.id}"
                notification_type = "reminder_on_shift"

            session.add(
                UserNotification(
                    user=reminder.user,
                    text=text_to_send,
                    notification_type=notification_type,
                    url=url_endpoint,
                )
            )
            while True:
                reminder.number_of_reminders -= 1
                reminder.next_reminder += timedelta(days=reminder.reminder_delay)
                if (
                    reminder.next_reminder > Time(now, format='datetime')
                    or reminder.number_of_reminders == 0
                ):
                    break
            session.add(reminder)
            session.commit()

            ws_flow.push(reminder.user.id, "skyportal/FETCH_NOTIFICATIONS")


if __name__ == "__main__":
    service()
