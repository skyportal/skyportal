import time
import traceback
from datetime import timedelta

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import User, init_db
from baselayer.log import make_log
from skyportal.app_utils import get_app_base_url
from skyportal.email_utils import send_email
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
from skyportal.utils.naive_datetime import utcnow_naive
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("reminders")

MAX_SLEEP = cfg.get("misc", {}).get("max_seconds_to_sleep_reminders_service", 60)


def send_reminders():
    sleep_time = MAX_SLEEP
    now = utcnow_naive()
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
            extra_email_html = ""
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
                extra_email_html = (
                    "<ul>"
                    f"<li>Start: {shift.start_date.strftime('%Y-%m-%d %H:%M')} UTC</li>"
                    f"<li>End: {shift.end_date.strftime('%Y-%m-%d %H:%M')} UTC</li>"
                    + (
                        f"<li>Description: {shift.description}</li>"
                        if shift.description
                        else ""
                    )
                    + "</ul>"
                )
            else:
                raise ValueError(f"Unknown reminder type: {reminder_type}")

            reminder_prefs = (
                (reminder.user.preferences or {})
                .get("notifications", {})
                .get("reminders", {})
            )
            type_enabled = reminder_prefs.get(notification_type, False)
            if (
                reminder_prefs.get("active")
                and type_enabled
                and reminder_prefs.get("email", {}).get("active")
                and reminder.user.contact_email
            ):
                try:
                    app_url = get_app_base_url()
                    plain_text = text_to_send.replace("*", "")
                    send_email(
                        recipients=[reminder.user.contact_email],
                        subject=f"{cfg['app.title']} - {plain_text}",
                        body=(
                            "<!DOCTYPE html><html><head>"
                            "<style>body {font-family: Arial, Helvetica, sans-serif;}</style>"
                            "</head><body>"
                            f"<p>{plain_text}</p>"
                            f"{extra_email_html}"
                            f"<p><a href='{app_url}{url_endpoint}'>View in {cfg['app.title']}</a></p>"
                            "</body></html>"
                        ),
                    )
                except Exception as e:
                    log(
                        f"Failed to send reminder email to {reminder.user.contact_email}: {e}"
                    )

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
            dt = (next_reminder.next_reminder - now).total_seconds()
            sleep_time = min(sleep_time, dt)

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
