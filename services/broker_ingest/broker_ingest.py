"""In-core broker ingestion service.

Runs each active `Broker` whose provider implements `run_ingestion` (a
long-running consumer: Kafka/REST -> shared save transform). One asyncio task
per broker in a single event loop; the providers offload blocking I/O (e.g.
Kafka poll) via `asyncio.to_thread` so brokers don't starve each other.

Scales out to `brokers.ingest_processes` OS processes (supervisor numprocs).
Process 0 runs every broker; higher-index processes run only providers whose
ingestion is safe to replicate (a shared Kafka consumer group Kafka rebalances),
so REST-polling providers are not duplicated.

Enable with `brokers.ingest_enabled: true` in the config.
"""

import asyncio
import sys

import sqlalchemy as sa

from baselayer.app import models as baselayer_models
from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import Broker

env, cfg = load_env()
log = make_log("broker_ingest")

init_db(**cfg["database"])

# This process's index within the broker_ingest program (supervisor --process).
_PROCESS_INDEX = 0
for _arg in sys.argv[1:]:
    if _arg.startswith("--process="):
        try:
            _PROCESS_INDEX = int(_arg.split("=", 1)[1])
        except ValueError:
            pass

# How often to re-scan the DB for newly-added / activated brokers.
RESCAN_INTERVAL = 60  # seconds


async def _run_broker(broker):
    """Run one broker's ingestion loop, logging (not raising) on failure so a
    single broker crash doesn't take down the service."""
    try:
        await broker.broker_class.run_ingestion(broker)
    except Exception as e:
        log(f"broker {broker.id} ({broker.name}) ingestion crashed: {e}")


async def _active_ingestion_brokers(session):
    brokers = (
        await session.scalars(sa.select(Broker).where(Broker.active.is_(True)))
    ).all()
    wanted = {}
    for b in brokers:
        try:
            if not b.broker_class.implements().get("run_ingestion"):
                continue
            # Replica processes run only providers safe to replicate across a
            # shared Kafka consumer group; REST pollers stay on process 0.
            if _PROCESS_INDEX > 0 and not getattr(
                b.broker_class, "parallel_ingestion", False
            ):
                continue
            session.expunge(b)  # detached: used from a long-lived task
            wanted[b.id] = b
        except Exception as e:
            log(f"skipping broker {b.id}: {e}")
    return wanted


async def _run_loop():
    running: dict[int, asyncio.Task] = {}
    while True:
        try:
            # Resolve on the baselayer module at call time: init_db() rebinds the
            # global there, but skyportal.models star-imported it as None at import
            # time and keeps that stale binding.
            async with baselayer_models.async_plain_session_factory() as session:
                wanted = await _active_ingestion_brokers(session)
        except Exception as e:
            log(f"failed to list brokers: {e}")
            wanted = {}

        for bid, broker in wanted.items():
            task = running.get(bid)
            if task is None or task.done():
                log(f"starting ingestion for broker {bid} ({broker.name})")
                running[bid] = asyncio.create_task(_run_broker(broker))

        await asyncio.sleep(RESCAN_INTERVAL)


if __name__ == "__main__":
    if not cfg.get("brokers.ingest_enabled", False):
        log("broker ingestion disabled (set brokers.ingest_enabled: true to enable)")
        # Idle instead of exiting so supervisor doesn't restart-loop.
        import time

        while True:
            time.sleep(3600)
    else:
        log(f"broker_ingest process {_PROCESS_INDEX} starting")
        asyncio.run(_run_loop())
