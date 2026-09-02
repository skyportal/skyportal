import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ....models import GcnEvent, GcnEventExtraction, Localization
from ...base import BaseHandler

default_prefs = {"maxNumGcnEvents": 10}


def latest_extraction_per_event():
    """Newest extraction timestamp for each event, as a joinable subquery."""
    return (
        sa.select(
            GcnEventExtraction.dateobs.label("dateobs"),
            sa.func.max(GcnEventExtraction.created_at).label("last_extraction"),
        )
        .group_by(GcnEventExtraction.dateobs)
        .subquery()
    )


def order_by_recent_activity(query, activity):
    """Order events by the later of the event time and its newest circular.

    A burst from last week whose circular arrived this morning is current news,
    so ordering on `dateobs` alone would bury it. `created_at` is when the
    extraction was written, which tracks circular arrival for a live feed; a
    bulk backfill of the archive would stamp them all at once and flatten this.
    """
    return query.outerjoin(activity, GcnEvent.dateobs == activity.c.dateobs).order_by(
        sa.func.greatest(
            GcnEvent.dateobs,
            sa.func.coalesce(activity.c.last_extraction, GcnEvent.dateobs),
        ).desc()
    )


class RecentGcnEventsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        description: Retrieve recent GCN events
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: GcnEventHandlerGet
          400:
            content:
              application/json:
                schema: Error
        """
        user_prefs = getattr(self.current_user, "preferences", None) or {}
        recent_events_prefs = user_prefs.get("recentGcnEvents", {})
        recent_events_prefs = {**default_prefs, **recent_events_prefs}

        max_num_events = (
            int(recent_events_prefs["maxNumEvents"])
            if "maxNumEvents" in recent_events_prefs
            else 5
        )
        async with self.AsyncSession() as session:
            # event.localizations.tags is traversed below, so chain
            # selectinload to that depth. joinedload would also work but
            # selectinload composes more cleanly with `.unique().all()`.
            activity = latest_extraction_per_event()
            result = await session.scalars(
                order_by_recent_activity(
                    GcnEvent.select(
                        session.user_or_token,
                        options=[
                            selectinload(GcnEvent.localizations).selectinload(
                                Localization.tags
                            ),
                            selectinload(GcnEvent.gcn_triggers),
                            # event.tags reads the _tags relationship below; eager-load
                            # it so the property doesn't lazy-load (MissingGreenlet) here.
                            selectinload(GcnEvent._tags),
                        ],
                    ),
                    activity,
                ).limit(max_num_events)
            )
            q = result.unique().all()
            events = []
            for event in q:
                event_info = {**event.to_dict(), "tags": list(set(event.tags))}
                event_info["localizations"] = sorted(
                    (
                        {
                            **loc.to_dict(),
                            "tags": [tag.to_dict() for tag in loc.tags],
                        }
                        for loc in event.localizations
                    ),
                    key=lambda x: x["created_at"],
                    reverse=True,
                )
                events.append(event_info)

            return self.success(data=events)
