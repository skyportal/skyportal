import asyncio
import json
import time
import traceback
import urllib
from datetime import datetime, timedelta
from threading import Thread

import conesearch_alchemy as ca
import requests
import sqlalchemy as sa
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.netutil
import tornado.web
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.handlers.api.photometry import add_external_photometry
from skyportal.handlers.api.source import post_source
from skyportal.handlers.api.spectrum import post_spectrum
from skyportal.models import (
    DBSession,
    Group,
    Obj,
    Source,
    TNSRetrievalTask,
    User,
)
from skyportal.utils.calculations import great_circle_distance
from skyportal.utils.coordination import service_leader_lock
from skyportal.utils.parse import is_null
from skyportal.utils.services import check_loaded
from skyportal.utils.tns import (
    TNS_URL,
    get_IAUname,
    get_recent_TNS,
    get_tns_headers,
    get_tns_url,
    read_tns_photometry,
    read_tns_spectrum,
)

env, cfg = load_env()
log = make_log("tns_queue")

init_db(**cfg["database"])

Session = scoped_session(sessionmaker())

USER_ID = 1  # super admin user ID
DEFAULT_RADIUS = 2.0 / 3600  # 2 arcsec in degrees

bot_id = cfg.get("app.tns.bot_id", None)
bot_name = cfg.get("app.tns.bot_name", None)
api_key = cfg.get("app.tns.api_key", None)
look_back_days = cfg.get("app.tns.look_back_days", 1)


def refresh_obj_on_frontend(obj, user_id="*"):
    """Refresh an object's source page on the frontend for all users or a specific user.

    Parameters
    ----------
    obj : `skyportal.models.Obj`
        The object to refresh, with an id and internal_key
    user_id : str, optional
        The user ID to refresh the object for. If '*', refresh for all users.
    """
    try:
        flow = Flow()
        flow.push(
            user_id,
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj.internal_key},
        )
    except Exception:
        log(f"Error refreshing object {obj.id} on frontend")


def add_tns_name_to_existing_objs(tns_name, tns_source_data, tns_ra, tns_dec, session):
    """Add TNS name to existing objects within 2 arcseconds of the TNS position.

    Parameters
    ----------
    tns_name : str
        TNS name (with prefix) to be added to the object
    tns_source_data : dict
        TNS source data to be added to the object as tns_info
    tns_ra : float
        Right ascension of the TNS source
    tns_dec : float
        Declination of the TNS source
    session : `sqlalchemy.orm.session.Session`
        Database session object
    """
    tns_name = str(tns_name).strip()
    other = ca.Point(ra=tns_ra, dec=tns_dec)
    existing_objs = session.scalars(
        sa.select(Obj).where(Obj.within(other, DEFAULT_RADIUS))  # 2 arcseconds
    ).all()
    if len(existing_objs) > 0:
        for obj in existing_objs:
            try:
                if obj.tns_name == tns_name:
                    continue
                elif obj.tns_name is None or obj.tns_name == "":
                    obj.tns_name = tns_name
                    obj.tns_info = tns_source_data
                # if the obj has tns_info that contains radeg and decdeg,
                # check if the new TNS source is closer to the obj than the existing TNS source
                elif (
                    isinstance(obj.tns_info, dict)
                    and "radeg" in obj.tns_info
                    and "decdeg" in obj.tns_info
                ):
                    existing_tns_dist = great_circle_distance(
                        obj.ra,
                        obj.dec,
                        float(obj.tns_info["radeg"]),
                        float(obj.tns_info["decdeg"]),
                    )
                    new_tns_dist = great_circle_distance(
                        obj.ra, obj.dec, float(tns_ra), float(tns_dec)
                    )
                    if new_tns_dist < existing_tns_dist:
                        obj.tns_name = tns_name
                        obj.tns_info = tns_source_data
                # if the current name doesn't have the SN designation but the new name has it, update
                elif not str(obj.tns_name).lower().strip().startswith(
                    "sn"
                ) and "AT" not in str(tns_name):
                    obj.tns_name = str(tns_name).strip()
                    obj.tns_info = tns_source_data
                else:
                    continue

                session.commit()
                log(f"Updated object {obj.id} with TNS name {tns_name}")
                refresh_obj_on_frontend(obj)
            except Exception as e:
                log(f"Error updating object: {str(e)}")
                session.rollback()


def add_tns_photometry(tns_name, tns_source, tns_source_data, public_group_id, session):
    """Add TNS photometry to a TNS source.

    Parameters
    ----------
    tns_name : str
        The full TNS name of the source, including the "AT" or "SN" prefix
    tns_source : str
        The TNS source, excluding the "AT" or "SN" prefix
    tns_source_data : dict
        The data retrieved from TNS for the source
    public_group_id : int
        The ID of the public group
    session : `sqlalchemy.orm.session.Session`
        Database session object
    """

    user = session.scalar(sa.select(User).where(User.id == USER_ID))
    if user is None:
        log(
            f"Error getting user {USER_ID}, required to add photometry with add_external_photometry()"
        )
        return

    photometry = tns_source_data.get("photometry", [])
    if len(photometry) == 0:
        log(f"No photometry found on TNS for source {tns_source}")
        return

    failed_photometry = []
    failed_photometry_errors = []
    for phot in photometry:
        try:
            df, instrument_id = read_tns_photometry(phot, session)
            data_out = {
                "obj_id": tns_source,
                "instrument_id": instrument_id,
                "group_ids": [public_group_id],
                **df.to_dict(orient="list"),
            }
            read_photometry = True
        except Exception as e:
            failed_photometry.append(phot)
            failed_photometry_errors.append(str(e))
            log(f"Cannot read TNS photometry {str(phot)}: {str(e)}")
            continue
        if read_photometry:
            try:
                add_external_photometry(data_out, user, parent_session=session)
            except Exception as e:
                failed_photometry.append(phot)
                failed_photometry_errors.append(str(e))
                continue

    if len(failed_photometry) > 0:
        log(
            f"Failed to retrieve {len(failed_photometry)}/{len(photometry)} TNS photometry points from {tns_name}: {str(list(set(failed_photometry_errors)))}"
        )
    else:
        log(
            f"Successfully retrieved {len(photometry)} TNS photometry points from {tns_name}"
        )


def add_tns_spectra(tns_name, tns_source, tns_source_data, public_group_id, session):
    """Add TNS spectra to a TNS source.

    Parameters
    ----------
    tns_name : str
        The full TNS name of the source, including the "AT" or "SN" prefix
    tns_source : str
        The TNS source, excluding the "AT" or "SN" prefix
    tns_source_data : dict
        The data retrieved from TNS for the source
    public_group_id : int
        The ID of the public group
    session : `sqlalchemy.orm.session.Session`
        Database session object
    """
    spectra = tns_source_data.get("spectra", [])
    if len(spectra) == 0:
        log(f"No spectra found on TNS for source {tns_source}")
        return

    failed_spectra = []
    failed_spectra_errors = []

    for spectrum in spectra:
        try:
            data = read_tns_spectrum(spectrum, session)
        except Exception as e:
            log(f"Cannot read TNS spectrum {str(spectrum)}: {str(e)}")
            continue
        data["obj_id"] = tns_source
        data["group_ids"] = [public_group_id]
        post_spectrum(data, USER_ID, session)

    if len(failed_spectra) > 0:
        log(
            f"Failed to retrieve {len(failed_spectra)}/{len(spectra)} TNS spectra from {tns_name}: {str(list(set(failed_spectra_errors)))}"
        )
    else:
        log(f"Successfully retrieved {len(spectra)} TNS spectra from {tns_name}")


def _notify_user_of_failure(user_id, ref, exc):
    """Best-effort frontend toast for the submitter when a task fails."""
    if user_id is None:
        return
    try:
        flow = Flow()
        if "not found on TNS" in str(exc):
            flow.push(
                user_id,
                action_type="baselayer/SHOW_NOTIFICATION",
                payload={"note": str(exc), "type": "warning"},
            )
        else:
            flow.push(
                user_id,
                action_type="baselayer/SHOW_NOTIFICATION",
                payload={
                    "note": f"Error processing TNS source {ref}: {exc}",
                    "type": "error",
                },
            )
    except Exception as flow_exc:
        log(f"Failed to push user notification for TNS task: {flow_exc}")


def process_queue():
    """Drain pending TNSRetrievalTask rows from the DB queue.

    Each replica claims one row at a time via FOR UPDATE SKIP LOCKED, holds
    the lock for the duration of the (possibly slow) TNS fetch + DB writes,
    then marks the task 'done' or 'failed' and commits. Concurrent replicas
    naturally split work.
    """
    if TNS_URL is None or bot_id is None or bot_name is None or api_key is None:
        log("TNS watcher not configured, skipping")
        return
    tns_headers = get_tns_headers(bot_id, bot_name)

    while True:
        try:
            processed = _claim_and_process_one(tns_headers)
            if not processed:
                time.sleep(1)
        except Exception as e:
            log(f"Unexpected error draining TNS queue: {e}")
            traceback.print_exc()
            time.sleep(5)


def _claim_and_process_one(tns_headers):
    """Returns True if a task was claimed (regardless of outcome), False if idle."""
    with DBSession() as session:
        task = session.scalars(
            sa.select(TNSRetrievalTask)
            .where(TNSRetrievalTask.status == "pending")
            .with_for_update(skip_locked=True)
            .limit(1)
        ).first()
        if task is None:
            return False

        # Identify the task's reference for logs/notifications before any
        # mutations -- the ORM object stays attached to the session.
        ref = task.tns_source or task.obj_id
        user_id = task.user_id

        try:
            _process_task(session, task, tns_headers)
            task.status = "done"
        except Exception as e:
            traceback.print_exc()
            log(f"Error processing TNS task {task.id} ({ref}): {e}")
            task.status = "failed"
            task.error = str(e)[:5000]
            _notify_user_of_failure(user_id, ref, e)

        session.commit()
    return True


def _process_task(session, task, tns_headers):
    """Carry out a single TNS retrieval. Raises on failure."""
    public_group = session.scalar(
        sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
    )
    if public_group is None:
        raise RuntimeError(f"Public group {cfg['misc.public_group_name']} not found")
    public_group_id = public_group.id

    existing_obj = None
    tns_name = None

    if task.obj_id is not None:
        existing_obj = session.scalar(sa.select(Obj).where(Obj.id == task.obj_id))
        if existing_obj is None:
            raise ValueError(f"Object {task.obj_id} not found in the database")

        tns_prefix, tns_source = get_IAUname(
            api_key,
            tns_headers,
            ra=existing_obj.ra,
            dec=existing_obj.dec,
            radius=float(task.radius if task.radius is not None else DEFAULT_RADIUS),
            closest=True,
        )
        log(
            f"Found TNS source {tns_source} for object {existing_obj.id} "
            f"with prefix {tns_prefix}"
        )
        if is_null(tns_source):
            raise ValueError(f"{task.obj_id} not found on TNS.")
        tns_name = f"{tns_prefix} {tns_source}"
    elif task.tns_source:
        tns_source = task.tns_source
        tns_prefix = task.tns_prefix
        tns_name = f"{tns_prefix} {tns_source}" if tns_prefix else tns_source
        log(f"Processing TNS source {tns_name}")
    else:
        raise ValueError("Task has neither obj_id nor tns_source")

    # Fetch the data from TNS, with retries on 429.
    data = {
        "api_key": api_key,
        "data": json.dumps(
            {
                "objname": tns_source,
                "photometry": 1,
                "spectra": 1,
            }
        ),
    }
    max_retries = 24
    retry_delay = 10
    r = None
    status_code = None
    for _ in range(max_retries):
        r = requests.post(
            get_tns_url("object"),
            headers=tns_headers,
            data=data,
            allow_redirects=True,
            stream=True,
            timeout=10,
        )
        status_code = r.status_code
        if status_code != 429:
            break
        time.sleep(retry_delay)

    if status_code != 200:
        raise RuntimeError(f"TNS returned {status_code} for {tns_name}: {r.text}")

    try:
        tns_source_data = r.json().get("data", {})
    except Exception:
        tns_source_data = None
    if tns_source_data is None:
        raise RuntimeError(f"TNS reply for {tns_name} had no data field")

    # '110' is the TNS code we get when an object is not found
    msg = tns_source_data.get("name", {}).get("110", {}).get("message", None)
    if msg == "No results found.":
        raise ValueError(f"{tns_source} not found on TNS at {TNS_URL}")

    tns_prefix = tns_source_data.get("name_prefix", None)
    if tns_prefix is None:
        raise RuntimeError(f"TNS source {tns_name} has no prefix ({r.json()})")

    tns_name = f"{tns_prefix} {tns_source}"
    ra = tns_source_data.get("radeg", None)
    dec = tns_source_data.get("decdeg", None)
    if ra is None or dec is None:
        raise RuntimeError(f"TNS source {tns_name} missing coordinates")

    if existing_obj:
        existing_obj.tns_name = tns_name
        existing_obj.tns_info = tns_source_data
        session.flush()
        refresh_obj_on_frontend(existing_obj)
    else:
        add_tns_name_to_existing_objs(tns_name, tns_source_data, ra, dec, session)

    # Public source creation / update (used to live in a second DBSession;
    # we now keep it on the same session so the TNSRetrievalTask row stays
    # locked through the entire operation).
    existing_tns_obj = session.scalar(sa.select(Obj).where(Obj.id == tns_source))
    existing_tns_public_source = session.scalar(
        sa.select(Source).where(
            Source.obj_id == tns_source,
            Source.group_id == public_group_id,
        )
    )
    if existing_tns_obj and existing_tns_obj.tns_name != tns_name:
        existing_tns_obj.tns_name = tns_name
        existing_tns_obj.tns_info = tns_source_data
        session.flush()
        log(f"TNS obj {tns_name} already exists in the database, updated its TNS name.")
        refresh_obj_on_frontend(existing_tns_obj)

    if existing_tns_public_source is None:
        log(f"Saving TNS source {tns_name} to the database (public group)")
        new_source_data = {
            "id": tns_source,
            "ra": ra,
            "dec": dec,
            "tns_name": tns_name,
            "tns_info": tns_source_data,
            "group_ids": [public_group_id],
        }
        post_source(new_source_data, USER_ID, session)

        add_tns_photometry(
            tns_name,
            tns_source,
            tns_source_data,
            public_group_id,
            session,
        )

        add_tns_spectra(
            tns_name,
            tns_source,
            tns_source_data,
            public_group_id,
            session,
        )


def _pending_count(session):
    return session.scalar(
        sa.select(sa.func.count(TNSRetrievalTask.id)).where(
            TNSRetrievalTask.status == "pending"
        )
    )


def tns_watcher():
    """Periodically poll TNS for recent sources and enqueue tasks for them.

    Wraps each tick in a transactional advisory lock so only one replica
    actually hits the TNS API per tick (saves rate-limit budget). Other
    replicas' ticks are no-ops and resume on the next interval.
    """
    if not TNS_URL or not bot_id or not bot_name or not api_key or not look_back_days:
        log("TNS watcher not configured, skipping")
        return
    tns_headers = get_tns_headers(bot_id, bot_name)

    # Process-local start_date. After a failover the new leader starts from
    # `look_back_days` ago; duplicate enqueues are skipped at insert time
    # (we filter on existing pending/processing rows for the same tns_source).
    start_date = datetime.now() - timedelta(days=look_back_days)

    while True:
        try:
            with DBSession() as session:
                with service_leader_lock(session, "tns_watcher") as got_lock:
                    if got_lock:
                        try:
                            tns_sources = get_recent_TNS(
                                api_key,
                                tns_headers,
                                start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                get_data=False,
                            )
                        except Exception as e:
                            log(
                                f"Error getting TNS sources: {e}, retrying in 4 minutes"
                            )
                            tns_sources = []

                        enqueued = 0
                        for tns_source in tns_sources:
                            already = session.scalar(
                                sa.select(TNSRetrievalTask.id).where(
                                    TNSRetrievalTask.tns_source == tns_source["id"],
                                    TNSRetrievalTask.status.in_(
                                        ["pending", "processing"]
                                    ),
                                )
                            )
                            if already is not None:
                                continue
                            session.add(
                                TNSRetrievalTask(
                                    tns_prefix=tns_source["prefix"],
                                    tns_source=tns_source["id"],
                                    obj_id=None,
                                    status="pending",
                                    payload={
                                        "source": "watcher",
                                        "tns_prefix": tns_source["prefix"],
                                        "tns_source": tns_source["id"],
                                    },
                                )
                            )
                            log(
                                f"Added TNS source {tns_source['id']} "
                                f"to the queue for processing"
                            )
                            enqueued += 1

                        session.commit()

                        if tns_sources:
                            start_date = datetime.now() - timedelta(hours=1)
        except Exception as e:
            log(f"Unexpected error in tns_watcher tick: {e}")
            traceback.print_exc()

        time.sleep(60 * 4)


def api():
    """Internal HTTP endpoint: receives TNS requests and inserts task rows.

    The Tornado app binds with SO_REUSEPORT so N replicas can share the port.
    Each POST inserts a TNSRetrievalTask with status='pending'; the consumer
    loop in another thread (or another replica) picks it up via SKIP LOCKED.
    """

    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            with DBSession() as session:
                pending = _pending_count(session)
            self.write({"status": "success", "data": {"queue_length": pending}})

        async def post(self):
            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})

            if "tns_source" in data:
                with DBSession() as session:
                    session.add(
                        TNSRetrievalTask(
                            tns_source=data["tns_source"],
                            status="pending",
                            payload=data,
                        )
                    )
                    session.commit()
                    pending = _pending_count(session)
                self.set_status(200)
                return self.write(
                    {
                        "status": "success",
                        "message": "TNS request accepted into queue",
                        "data": {"queue_length": pending},
                    }
                )

            required_keys = {"obj_id", "user_id"}
            if not required_keys.issubset(set(data.keys())):
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"TNS requests requires keys {required_keys}",
                    }
                )

            with DBSession() as session:
                session.add(
                    TNSRetrievalTask(
                        obj_id=data["obj_id"],
                        user_id=data["user_id"],
                        radius=data.get("radius"),
                        status="pending",
                        payload=data,
                    )
                )
                session.commit()
                pending = _pending_count(session)
            self.set_status(200)
            return self.write(
                {
                    "status": "success",
                    "message": "TNS request accepted into queue",
                    "data": {"queue_length": pending},
                }
            )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    port = cfg["ports.tns_retrieval_queue"]
    try:
        sockets = tornado.netutil.bind_sockets(port, reuse_port=True)
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.add_sockets(sockets)
    except ValueError as e:
        log(
            f"SO_REUSEPORT unavailable ({e}); falling back to single-replica "
            f"bind on port {port}"
        )
        app.listen(port)
    loop.run_forever()


@check_loaded(logger=log)
def service(*args, **kwargs):
    """Spawn the three worker threads. Queue state lives in the DB now."""

    t = Thread(target=process_queue)
    t2 = Thread(target=api)
    t3 = Thread(target=tns_watcher)
    t.start()
    t2.start()
    t3.start()
    while True:
        try:
            with DBSession() as session:
                pending = _pending_count(session)
            log(f"Current TNS retrieval queue length: {pending}")
        except Exception as e:
            log(f"Failed to read pending TNS count: {e}")
        time.sleep(120)


if __name__ == "__main__":
    """Start the internal API, the TNS watcher, and the TNS retrieval service"""
    try:
        service()
    except Exception as e:
        log(f"Error occurred in TNS retrieval queue: {str(e)}")
