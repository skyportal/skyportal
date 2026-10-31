"""Broker backfill service.

A one-off counterpart to `broker_ingest`: where that follows a live stream, this
reaches back into a broker's own store for a single filter and ingests what the
stream no longer retains. Jobs arrive over HTTP from the app and run one at a
time, because each one spends an upstream call allowance that is shared across
whatever else that account is doing.

Runs regardless of `brokers.ingest_enabled`: a backfill touches no consumer
offset, so it is useful on an instance that streams nothing.
"""

import asyncio
import time
from threading import Thread

import sqlalchemy as sa
import tornado.escape
import tornado.web

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import Broker, BrokerCredential, Filter
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log("broker_backfill")

init_db(**cfg["database"])

# Seconds between two upstream object calls. The default suits Lasair's 100
# calls an hour; a provider with a different allowance passes its own.
DEFAULT_REQUEST_INTERVAL = cfg.get("brokers.backfill.min_request_interval", 45)
DEFAULT_LIMIT = cfg.get("brokers.backfill.limit", 1000)


async def _load_job(session, job):
    """The broker, filter and upstream token a job names, or a reason it cannot
    run. The token is the requesting user's own when they have credentials for
    the broker, since the filter may be private to their upstream account."""
    broker = await session.scalar(
        sa.select(Broker).where(Broker.id == job["broker_id"])
    )
    if broker is None:
        return None, None, None, f"no broker with id {job['broker_id']}"
    if not broker.active:
        return None, None, None, f"broker {broker.id} is not active"
    if not getattr(broker.broker_class, "supports_backfill", False):
        return None, None, None, f"{broker.broker_classname} cannot backfill"
    filter_row = await session.scalar(
        sa.select(Filter).where(Filter.id == job["filter_id"])
    )
    if filter_row is None:
        return None, None, None, f"no filter with id {job['filter_id']}"
    credential = await session.scalar(
        sa.select(BrokerCredential).where(
            BrokerCredential.broker_id == broker.id,
            BrokerCredential.user_id == job["user_id"],
        )
    )
    token = credential.altdata.get("token") if credential is not None else None
    return broker, filter_row, token, None


async def _run_job(job):
    from baselayer.app.models import async_plain_session_factory

    async with async_plain_session_factory() as session:
        broker, filter_row, token, problem = await _load_job(session, job)
    if problem is not None:
        log(f"refusing backfill: {problem}")
        return
    try:
        await broker.broker_class.run_backfill(
            broker,
            filter_row,
            token=token,
            limit=job.get("limit") or DEFAULT_LIMIT,
            interval=job.get("interval", DEFAULT_REQUEST_INTERVAL),
        )
    except Exception as e:
        log(f"backfill of filter {job['filter_id']} failed: {e}")


def process_queue(queue):
    """Run queued backfills one at a time, forever."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        if not queue:
            time.sleep(1)
            continue
        job = queue[0]
        try:
            loop.run_until_complete(_run_job(job))
        except Exception as e:
            # One job must never take the worker down.
            log(f"error processing backfill {job}: {e}")
        finally:
            queue.pop(0)
        time.sleep(job.get("interval", DEFAULT_REQUEST_INTERVAL))


def api(queue):
    """Accept backfill jobs from the app."""

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

            required = {"broker_id", "filter_id", "user_id"}
            missing = required - set(data)
            if missing:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": f"A backfill requires {sorted(required)}",
                    }
                )
            # Covers the running job too, which stays first in the queue until done.
            if any(
                job["broker_id"] == data["broker_id"]
                and job["filter_id"] == data["filter_id"]
                for job in queue
            ):
                self.set_status(409)
                return self.write(
                    {
                        "status": "error",
                        "message": "That filter is already queued or running",
                    }
                )

            queue.append(data)
            self.set_status(200)
            return self.write(
                {
                    "status": "success",
                    "message": "Backfill accepted into queue",
                    "data": {"queue_length": len(queue)},
                }
            )

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.broker_backfill"])
    loop.run_forever()


@check_loaded(logger=log)
def service(*args, **kwargs):
    """Run the backfill queue."""
    queue = []
    worker = Thread(target=process_queue, args=(queue,), daemon=True)
    endpoint = Thread(target=api, args=(queue,), daemon=True)
    worker.start()
    endpoint.start()
    while True:
        time.sleep(120)
        # Exit if a worker died so supervisor restarts us, rather than sitting
        # here accepting work nothing will answer.
        if not (worker.is_alive() and endpoint.is_alive()):
            log("A broker backfill worker died, exiting for supervisor restart")
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error occurred in broker backfill queue: {str(e)}")
