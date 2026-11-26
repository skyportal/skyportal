import asyncio
import uuid
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app import models
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db, session_context_id
from baselayer.log import make_log
from skyportal.facility_apis.lco import LCOAPI
from skyportal.models import Allocation, FollowupRequest, Instrument
from skyportal.utils.naive_datetime import utcnow_naive
from skyportal.utils.services import check_loaded

_, cfg = load_env()
log = make_log("followup_status_refresh")

init_db(**cfg["database"])

INTERVAL_SECONDS = 3600
LOOK_BACK_DAYS = 60
API_CLASSNAMES = [api.__name__ for api in LCOAPI.__subclasses__()]


async def refresh(request_id):
    async with models.async_plain_session_factory() as session:
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request_id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )
        status = request.status
        await request.instrument.api_class.get(request, session)
        if request.status != status:
            log(f"Request {request_id}: {status} -> {request.status}")
            Flow().push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": request.obj.internal_key},
            )


async def refresh_all():
    session_context_id.set(uuid.uuid4().hex)
    async with models.async_plain_session_factory() as session:
        request_ids = (
            await session.scalars(
                sa.select(FollowupRequest.id)
                .join(Allocation)
                .join(Instrument)
                .where(
                    Instrument.api_classname.in_(API_CLASSNAMES),
                    FollowupRequest.status.in_(["submitted", "pending"]),
                    FollowupRequest.created_at
                    >= utcnow_naive() - timedelta(days=LOOK_BACK_DAYS),
                )
            )
        ).all()
    for request_id in request_ids:
        try:
            await refresh(request_id)
        except Exception as e:
            log(f"Error refreshing request {request_id}: {e}")


async def run():
    while True:
        try:
            await refresh_all()
        except Exception as e:
            log(f"Error refreshing follow-up requests: {e}")
        await asyncio.sleep(INTERVAL_SECONDS)


@check_loaded(logger=log)
def service(*args, **kwargs):
    asyncio.run(run())


if __name__ == "__main__":
    service()
