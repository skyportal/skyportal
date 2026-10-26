import arrow
import sqlalchemy as sa
from skyportal_py_models.gcn_events import GcnEventCrossmatchRequeueBody

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ...models import Filter, GcnEvent, GcnEventCrossmatchState
from ..base import BaseHandler

log = make_log("api/gcn_crossmatch")


class GcnEventCrossmatchHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs):
        """
        ---
        summary: Crossmatch progress for a GCN event
        description: |
          Per-filter state of the alert crossmatch for this event: when it was
          last queried, how far through the alert stream it has got, how many
          matches it has saved, and any error.
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            dateobs = arrow.get(dateobs.strip()).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            # selecting the event first means a user who cannot read it gets
            # "not found" rather than an empty progress list, which would
            # confirm the event exists
            event = await session.scalar(
                GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
            )
            if event is None:
                return self.error(f"No GCN event with dateobs {dateobs}")

            states = (
                await session.scalars(
                    GcnEventCrossmatchState.select(session.user_or_token).where(
                        GcnEventCrossmatchState.gcnevent_id == event.id
                    )
                )
            ).all()
            return self.success(data=[s.to_dict() for s in states])

    @permissions(["Manage GCNs"])
    async def post(self, dateobs, *, body: GcnEventCrossmatchRequeueBody = None):
        """
        ---
        summary: Requeue the alert crossmatch for a GCN event
        description: |
          Reset this event's crossmatch progress so the next service pass
          re-queries it from the start of the window, including the one-shot
          archival pass. Give a ``filter_id`` to requeue one filter alone;
          without one every filter on the event is requeued, and each one
          re-queries the broker.

          Existing sources and annotations are left alone: the crossmatch
          updates them in place, so re-running refreshes rather than
          duplicates. Use this after changing the quality-cut filter or the
          search parameters.
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(GcnEventCrossmatchRequeueBody)
        filter_id = body.filter_id

        try:
            dateobs = arrow.get(dateobs.strip()).naive
        except Exception as e:
            return self.error(f"Invalid dateobs: {e}")

        async with self.AsyncSession() as session:
            event = await session.scalar(
                GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
            )
            if event is None:
                return self.error(f"No GCN event with dateobs {dateobs}")

            stmt = sa.update(GcnEventCrossmatchState).where(
                GcnEventCrossmatchState.gcnevent_id == event.id
            )
            if filter_id is not None:
                # Checked against the requester's own access, so this cannot
                # be used to probe for filters they cannot see.
                filter_ = await session.scalar(
                    Filter.select(session.user_or_token).where(Filter.id == filter_id)
                )
                if filter_ is None:
                    return self.error(f"No filter with ID {filter_id}")
                stmt = stmt.where(GcnEventCrossmatchState.filter_id == filter_id)

            result = await session.execute(
                stmt.values(
                    status="pending",
                    last_queried=None,
                    last_alert_jd=None,
                    archival_done=False,
                    error=None,
                )
            )
            await session.commit()

            scope = f" filter {filter_id}" if filter_id is not None else ""
            log(
                f"Requeued crossmatch for {dateobs}{scope} "
                f"({result.rowcount} filter(s))"
            )
            return self.success(data={"filters_requeued": result.rowcount})
