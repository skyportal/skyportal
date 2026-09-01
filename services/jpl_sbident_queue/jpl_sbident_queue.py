"""Check objects against JPL's Small-Body Identification API and annotate the
result.

Scanning an EP queue by hand means opening every source page to ask whether the
candidate is a known minor planet. This answers that question in the background
and writes it onto the object, so it can be filtered on instead of looked up.

Queued rather than called inline: JPL's refining pass takes minutes, far longer
than a request handler can wait. Checks are answered one at a time, spaced out;
the API answers per field of view, so candidates seen in the same exposure could
share a call, which is the obvious way to make a large queue cheaper.
"""

import asyncio
import time
from datetime import datetime
from threading import Thread

import sqlalchemy as sa
import tornado.escape
import tornado.ioloop
import tornado.web
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import Annotation, DBSession, Group, Obj, User
from skyportal.utils.jpl_sbident import (
    DEFAULT_MATCH_ARCSEC,
    JPLSBIdentError,
    identify,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()
init_db(**cfg["database"])

log = make_log("jpl_sbident_queue")

Session = scoped_session(sessionmaker())

ANNOTATION_ORIGIN = "JPL-sbident"

# JPL is a shared, free service; one query at a time with a gap between them.
REQUEST_SPACING_SECONDS = 5


def _annotation_data(matches):
    """What a check learned, as flat keys so the source and candidate filters
    can read them directly."""
    data = {"sb_n_matches": len(matches)}
    if matches:
        nearest = matches[0]
        data["sb_name"] = nearest["name"]
        data["sb_offset_arcsec"] = nearest["offset_arcsec"]
        if "magnitude" in nearest:
            data["sb_magnitude"] = nearest["magnitude"]
    return data


def write_annotation(session, obj_id, user, group_ids, matches):
    """Attach (or refresh) this object's identification result."""
    data = _annotation_data(matches)
    annotation = session.scalar(
        Annotation.select(user, mode="update").where(
            Annotation.obj_id == obj_id, Annotation.origin == ANNOTATION_ORIGIN
        )
    )
    if annotation is None:
        annotation = Annotation(
            obj_id=obj_id, origin=ANNOTATION_ORIGIN, data=data, author_id=user.id
        )
        annotation.groups = session.scalars(
            sa.select(Group).where(Group.id.in_(group_ids))
        ).all()
        session.add(annotation)
    else:
        # A later check supersedes an earlier one: the orbit may have improved.
        annotation.data = data
    session.commit()
    return data


def process_queue(queue):
    """Answer queued checks, spacing the calls out."""
    while True:
        if not queue:
            time.sleep(1)
            continue

        task = queue.pop(0)
        obj_id = task.get("obj_id")
        try:
            if Session.registry.has():
                session = Session()
            else:
                session = Session(bind=DBSession.session_factory.kw["bind"])

            user = session.get(User, task["user_id"])
            obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()
            if obj is None:
                log(f"{obj_id}: not found or not readable, skipping")
                continue

            obs_time = task.get("obs_time")
            if isinstance(obs_time, str):
                obs_time = datetime.fromisoformat(obs_time)
            if obs_time is None:
                # A minor planet is only "here" at a time; without one there is
                # nothing to ask.
                log(f"{obj_id}: no observation time, skipping")
                continue

            matches = identify(
                obj.ra,
                obj.dec,
                obs_time,
                obscode=task.get("obscode", "500"),
                max_arcsec=task.get("max_arcsec", DEFAULT_MATCH_ARCSEC),
            )
            data = write_annotation(
                session, obj_id, user, task.get("group_ids") or [], matches
            )
            log(f"{obj_id}: {data['sb_n_matches']} match(es) {data}")

            flow = Flow()
            flow.push(
                "*", "skyportal/REFRESH_SOURCE", payload={"obj_key": obj.internal_key}
            )
        except JPLSBIdentError as e:
            # A refusal or a timeout is about this call, not the queue: the next
            # task is unaffected, and the object can be asked about again.
            log(f"{obj_id}: identification failed ({e})")
        except Exception as e:
            log(f"{obj_id}: error processing check ({e})")
        finally:
            Session.remove()
            time.sleep(REQUEST_SPACING_SECONDS)


def api(queue):
    """Accept checks from the app."""

    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write({"status": "success", "data": {"queue_length": len(queue)}})

        def post(self):
            try:
                data = tornado.escape.json_decode(self.request.body)
            except Exception:
                self.set_status(400)
                return self.write(
                    {"status": "error", "message": "Body must be valid JSON"}
                )

            required = {"obj_id", "user_id", "obs_time"}
            missing = required - set(data)
            if missing:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"Identification requires {sorted(required)}",
                    }
                )

            queue.append(data)
            self.set_status(200)
            return self.write(
                {
                    "status": "success",
                    "message": "Identification accepted into queue",
                    "data": {"queue_length": len(queue)},
                }
            )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.jpl_sbident_queue"])
    loop.run_forever()


@check_loaded(logger=log)
def service(*args, **kwargs):
    """Run the identification queue."""
    queue = []
    worker = Thread(target=process_queue, args=(queue,))
    endpoint = Thread(target=api, args=(queue,))
    worker.start()
    endpoint.start()
    while True:
        log(f"Current JPL identification queue length: {len(queue)}")
        time.sleep(120)
        # Exit if a worker died so supervisor restarts us, rather than sitting
        # here accepting work nothing will answer.
        if not (worker.is_alive() and endpoint.is_alive()):
            log("A JPL identification worker died, exiting for supervisor restart")
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error occurred in JPL identification queue: {str(e)}")
