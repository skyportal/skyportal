import os
import time

from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.earthquake import post_earthquake_from_xml
from skyportal.models import DBSession
from skyportal.utils.coordination import service_leader_session_lock

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("pdlserver")


def service():
    # Single-leader: only one replica runs the filesystem watcher at a time.
    # The lock is on a dedicated DB connection held for the lifetime of the
    # leader's tick; if the leader process dies, the connection closes and
    # the lock releases, so another replica takes over on its next attempt.
    # This makes pdl_service safe for shared-FS deployments (both replicas
    # would otherwise observe the same modify events and double-insert), and
    # is a no-op in per-host deployments since only one replica even exists
    # in that topology.
    while True:
        try:
            user_id = 1
            path = "services/pdl_service/data/receiver_storage/origin"
            os.makedirs(path, exist_ok=True)

            engine = DBSession.session_factory.kw["bind"]
            with service_leader_session_lock(engine, "pdl_service") as got_lock:
                if not got_lock:
                    # Another replica is the active watcher. Sleep before
                    # retrying so we don't hot-spin on the lock probe.
                    time.sleep(60)
                    continue

                with DBSession() as session:

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
            log(f"Failed to consume earthquake: {e}")


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error: {e}")
