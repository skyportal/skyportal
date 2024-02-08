import os
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.handlers.api.earthquake import post_earthquake_from_xml
from skyportal.models import (
    ThreadSession,
)

env, cfg = load_env()

init_db(**cfg['database'])

log = make_log('pdlserver')


def service():
    while True:
        try:
            user_id = 1
            path = "services/pdl_service/data/receiver_storage/origin"

            os.makedirs(path, exist_ok=True)

            with ThreadSession() as session:

                class Event(LoggingEventHandler):
                    def on_modified(self, event):
                        if "quakeml.xml" in event.src_path:
                            with open(event.src_path) as fid:
                                payload = fid.read()
                            post_earthquake_from_xml(payload, user_id, session)

                event_handler = Event()
                observer = Observer()
                observer.schedule(event_handler, path, recursive=True)
                observer.start()  # for starting the observer thread
                observer.join()

        except Exception as e:
            log(f'Failed to consume earthquake: {e}')


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f'Error: {e}')
