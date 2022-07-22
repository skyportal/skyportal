# For Michael, an example test run with Curl:
#
# curl -X POST http://localhost:64510 -d '{"method": "GET", "endpoint": "http://localhost:9980"}'
#

from astropy.time import Time
from datetime import datetime, timedelta
import asyncio
from tornado.ioloop import IOLoop
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

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('reminders')

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)


class ReminderQueue(asyncio.Queue):
    async def load_from_db(self):
        # Load items from database into queue
        while True:
            try:
                with DBSession() as session:
                    reminders = (
                        (
                            session.query(Reminder)
                            .where(Reminder.number_of_reminders != 0)
                            .all()
                        )
                        + (
                            session.query(ReminderOnSpectrum)
                            .where(ReminderOnSpectrum.number_of_reminders != 0)
                            .all()
                        )
                        + (
                            session.query(ReminderOnGCN)
                            .where(ReminderOnGCN.number_of_reminders != 0)
                            .all()
                            + (
                                session.query(ReminderOnShift)
                                .where(ReminderOnShift.number_of_reminders != 0)
                                .all()
                            )
                        )
                    )

                    for reminder in reminders:
                        await self.put([reminder.id, reminder.__class__])
                    break
            except Exception as e:
                log(e)
                await asyncio.sleep(5)

    async def service(self):
        last_update = datetime.utcnow()
        ws_flow = Flow()

        while True:
            try:
                with DBSession() as session:
                    reminders = (
                        (
                            session.query(Reminder)
                            .where(Reminder.created_at > last_update)
                            .all()
                        )
                        + (
                            session.query(ReminderOnSpectrum)
                            .where(ReminderOnSpectrum.created_at > last_update)
                            .all()
                        )
                        + (
                            session.query(ReminderOnGCN)
                            .where(ReminderOnGCN.created_at > last_update)
                            .all()
                        )
                        + (
                            session.query(ReminderOnShift)
                            .where(ReminderOnShift.created_at > last_update)
                            .all()
                        )
                    )
                    for reminder in reminders:
                        await self.put([reminder.id, reminder.__class__])

                    if len(reminders) > 0:
                        last_update = datetime.utcnow()

                # missing ? what happens if a reminder in the queue has been modified?
                # should we use: .where(ReminderOnShift.created_at > last_update) instead, and if a reminder is already in the queue,
                # we update it, if its not in the queue we just add it.
                if not self.empty():
                    reminder_id, reminder_type = await self.get()
                    with DBSession() as session:
                        reminder = session.query(reminder_type).get(reminder_id)
                        dt = Time(datetime.utcnow(), format='datetime') - Time(
                            reminder.next_reminder, format='datetime'
                        )
                        if dt < 0:
                            await self.put([reminder_id, reminder_type])
                        else:
                            log(f"Sending reminder {reminder.id}")

                            if reminder_type == Reminder:
                                text_to_send = f"Reminder of source *{reminder.obj_id}*: {reminder.text}"
                                url_endpoint = f"/source/{reminder.obj_id}"
                            elif reminder_type == ReminderOnSpectrum:
                                text_to_send = f"Reminder of spectrum *{reminder.spectrum_id}*: {reminder.text}"
                                url_endpoint = f"/source/{reminder.spectrum_id}"
                            elif reminder_type == ReminderOnGCN:
                                gcn_event = session.query(GcnEvent).get(reminder.gcn_id)
                                text_to_send = f"Reminder of GCN event *{gcn_event.dateobs}*: {reminder.text}"
                                url_endpoint = f"/gcn_events/{reminder.gcn_id}"
                            elif reminder_type == ReminderOnShift:
                                shift = session.query(Shift).get(reminder.shift_id)
                                text_to_send = (
                                    f"Reminder of shift *{shift.name}*: {reminder.text}"
                                )
                                url_endpoint = f"/shifts/{shift.id}"
                            else:
                                return self.error(
                                    f'Unknown reminder type "{reminder_type}".'
                                )

                            session.add(
                                UserNotification(
                                    user=reminder.user,
                                    text=text_to_send,
                                    notification_type="mention",
                                    url=url_endpoint,
                                )
                            )
                            ws_flow.push(
                                reminder.user.id, "skyportal/FETCH_NOTIFICATIONS"
                            )
                            loop = True
                            while loop:
                                reminder.number_of_reminders = (
                                    reminder.number_of_reminders - 1
                                )
                                if reminder.number_of_reminders > 0:
                                    reminder.next_reminder = (
                                        reminder.next_reminder
                                        + timedelta(days=reminder.reminder_delay)
                                    )
                                else:
                                    loop = False
                                if reminder.next_reminder > Time(
                                    datetime.utcnow(), format='datetime'
                                ):
                                    await self.put([reminder.id, reminder.__class__])
                                    loop = False
                            session.add(reminder)
                            session.commit()
            except Exception as e:
                log(e)
                await asyncio.sleep(5)


queue = ReminderQueue()

if __name__ == "__main__":
    loop = IOLoop.current()
    # loop.add_callback(queue.load_from_db)
    loop.add_callback(queue.service)
    loop.start()
