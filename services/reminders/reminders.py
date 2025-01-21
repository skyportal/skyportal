import time
import traceback
from datetime import datetime, timedelta, timezone

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import User, init_db
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    Reminder,
    ReminderOnGCN,
    ReminderOnShift,
    ReminderOnSpectrum,
    UserNotification,
)
from skyportal.models.gcn import GcnEvent
from skyportal.models.shift import Shift
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('reminders')


def send_reminders():
    sleep_time = 60
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reminders = []
    with DBSession() as session:
        user = session.query(User).where(User.id == 1).first()
        try:
            reminder_classes = [
                Reminder,
                ReminderOnSpectrum,
                ReminderOnGCN,
                ReminderOnShift,
            ]
            reminders = (
                session.scalars(
                    reminder_class.select(user)
                    .where(reminder_class.number_of_reminders > 0)
                    .where(reminder_class.next_reminder <= now)
                ).all()
                for reminder_class in reminder_classes
            )
            reminders = [reminder for sublist in reminders for reminder in sublist]
        except Exception as e:
            log(e)
            traceback.print_exc()

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
                url_endpoint = f"/gcn_events/{gcn_event.dateobs}"
                notification_type = "reminder_on_gcn"
            elif reminder_type == ReminderOnShift:
                shift = session.scalars(
                    Shift.select(user).where(Shift.id == reminder.shift_id)
                ).first()
                text_to_send = f"Reminder of shift *{shift.name}*: {reminder.text}"
                url_endpoint = f"/shifts/{shift.id}"
                notification_type = "reminder_on_shift"
            else:
                raise ValueError(f"Unknown reminder type: {reminder_type}")

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
                if reminder.next_reminder > now or reminder.number_of_reminders == 0:
                    break
            session.add(reminder)
            session.commit()

            ws_flow.push(reminder.user.id, "skyportal/FETCH_NOTIFICATIONS")

        next_reminders = []
        try:
            next_reminders = [
                session.scalars(
                    reminder_class.select(user)
                    .where(reminder_class.number_of_reminders > 0)
                    .where(reminder_class.next_reminder > now)
                    .where(
                        reminder_class.next_reminder
                        <= now + timedelta(seconds=sleep_time)
                    )
                    .order_by(reminder_class.next_reminder)
                    .limit(1)
                ).first()
                for reminder_class in reminder_classes
            ]
            next_reminders = [
                reminder for reminder in next_reminders if reminder is not None
            ]
        except Exception as e:
            log(e)
            traceback.print_exc()

        if len(next_reminders) > 0:
            next_reminder = min(next_reminders, key=lambda x: x.next_reminder)
            dt = (
                next_reminder.next_reminder
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
            send_reminders()
        except Exception as e:
            log(e)
            traceback.print_exc()


if __name__ == "__main__":
    service()
