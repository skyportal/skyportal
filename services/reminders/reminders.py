# For Michael, an example test run with Curl:
#
# curl -X POST http://localhost:64510 -d '{"method": "GET", "endpoint": "http://localhost:9980"}'
#

from astropy.time import Time
from datetime import datetime, timedelta
import time

import asyncio
from tornado.ioloop import IOLoop
import requests

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

env, cfg = load_env()

init_db(**cfg['database'])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)


class ReminderQueue(asyncio.Queue):
    async def load_from_db(self):
        # Load items from database into queue

        with DBSession() as session:
            reminders = (
                (session.query(Reminder).where(Reminder.number_of_reminders != 0).all())
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

    async def service(self):
        while True:

            reminder_id, reminder_type = await queue.get()

            with DBSession() as session:
                reminder = session.query(reminder_type).get(reminder_id)
                dt = Time(datetime.utcnow(), format='datetime') - Time(
                    reminder.next_reminder, format='datetime'
                )
                if dt.jd > 0:
                    await self.put([reminder_id, reminder_type])
                else:
                    print(f"Sending reminder {reminder.id}")

                    if reminder_type == Reminder:
                        text_to_send = (
                            f"Reminder of source *{reminder.obj_id}*: {reminder.text}"
                        )
                        url_endpoint = f"/source/{reminder.obj_id}"
                    elif reminder_type == ReminderOnSpectrum:
                        text_to_send = f"Reminder of spectrum *{reminder.spectrum_id}*: {reminder.text}"
                        url_endpoint = f"/source/{reminder.spectrum_id}"
                    elif reminder_type == ReminderOnGCN:
                        text_to_send = f"Reminder of GCN event *{reminder.gcnevent_id}*: {reminder.text}"
                        url_endpoint = f"/gcn_events/{reminder.gcnevent_id}"
                    elif reminder_type == ReminderOnShift:
                        text_to_send = (
                            f"Reminder of *shift {reminder.shift_id}*: {reminder.text}"
                        )
                        url_endpoint = "/shifts"
                    else:
                        return self.error(f'Unknown reminder type "{reminder_type}".')

                    session.add(
                        UserNotification(
                            user=reminder.user,
                            text=text_to_send,
                            notification_type="mention",
                            url=url_endpoint,
                        )
                    )

                    flow = Flow()
                    flow.push('*', "skyportal/FETCH_NOTIFICATIONS", {})

                    reminder.number_of_reminders = reminder.number_of_reminders - 1
                    if reminder.number_of_reminders > 0:
                        reminder.next_reminder = datetime.now() + timedelta(
                            days=reminder.reminder_delay
                        )
                        await self.put([reminder.id, reminder.__class__])

                    session.add(reminder)
                    session.commit()

                    time.sleep(10)


queue = ReminderQueue()

if __name__ == "__main__":
    loop = IOLoop.current()
    loop.add_callback(queue.load_from_db)
    loop.add_callback(queue.service)
    loop.start()
