#!/usr/bin/env python

import asyncio

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import new_async_session
from skyportal.broker_apis.boom import link_saved_counterparts
from skyportal.models import Broker, User, init_db

_, cfg = load_env()
init_db(**cfg["database"])


async def main():
    async with new_async_session() as session:
        user = await session.scalar(sa.select(User).where(User.id == 1))
        brokers = (
            await session.scalars(
                sa.select(Broker).where(
                    Broker.broker_classname == "BOOMBROKER",
                    Broker.active.is_(True),
                    Broker.ingest.is_(True),
                )
            )
        ).all()
        for broker in brokers:
            n_linked = await link_saved_counterparts(broker, session, user)
            print(f"Linked {n_linked} survey counterparts from {broker.name}.")


asyncio.run(main())
