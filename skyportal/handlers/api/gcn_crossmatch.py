import arrow
import sqlalchemy as sa

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ...models import GcnEvent, GcnEventCrossmatchState
from ..base import BaseHandler

log = make_log("api/gcn_crossmatch")


class GcnEventCrossmatchHandler(BaseHandler):
    @auth_or_token
    async def get(self, dateobs):
        """
        ---
        summary: Crossmatch progress for a GCN event
        description: |
          Per-broker state of the alert crossmatch for this event: when it was
          last queried, how far through the alert stream it has got, how many
          matches it has saved, and any error.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
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
    async def post(self, dateobs):
        """
        ---
        summary: Requeue the alert crossmatch for a GCN event
        description: |
          Reset this event's crossmatch progress so the next service pass
          re-queries every broker from the start of the window, including the
          one-shot archival pass.

          Existing sources and annotations are left alone: the crossmatch
          updates them in place, so re-running refreshes rather than
          duplicates. Use this after changing the quality-cut filter or the
          search parameters.
        tags:
          - gcn events
        parameters:
          - in: path
            name: dateobs
            required: true
            schema:
              type: string
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
            event = await session.scalar(
                GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == dateobs
                )
            )
            if event is None:
                return self.error(f"No GCN event with dateobs {dateobs}")

            result = await session.execute(
                sa.update(GcnEventCrossmatchState)
                .where(GcnEventCrossmatchState.gcnevent_id == event.id)
                .values(
                    status="pending",
                    last_queried=None,
                    last_alert_jd=None,
                    archival_done=False,
                    error=None,
                )
            )
            await session.commit()

            log(f"Requeued crossmatch for {dateobs} ({result.rowcount} broker(s))")
            return self.success(data={"brokers_requeued": result.rowcount})
