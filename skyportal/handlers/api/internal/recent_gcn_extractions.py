import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ....models import GcnEvent, GcnEventExtraction
from ...base import BaseHandler
from .recent_gcn_events import (
    latest_extraction_per_event,
    order_by_recent_activity,
)

# Matches the recent-events widget, whose events these are shown beneath.
default_prefs = {"maxNumEvents": 10}


class RecentGcnExtractionsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        description: Retrieve recent structured extractions from GCN circulars
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
        user_prefs = getattr(self.current_user, "preferences", None) or {}
        prefs = {**default_prefs, **user_prefs.get("recentGcnEvents", {})}
        try:
            max_num_events = int(prefs["maxNumEvents"])
        except (KeyError, TypeError, ValueError):
            max_num_events = default_prefs["maxNumEvents"]

        async with self.AsyncSession() as session:
            # Scope to the events the widget shows. Taking the most recent
            # extractions globally instead would silently drop any whose event
            # had already scrolled off the list beside it.
            activity = latest_extraction_per_event()
            recent_events = (
                order_by_recent_activity(
                    GcnEvent.select(session.user_or_token, columns=[GcnEvent.dateobs]),
                    activity,
                )
                .limit(max_num_events)
                .subquery()
            )
            # The event's aliases are rendered beside each extraction, so
            # eager-load it rather than lazy-loading inside the loop.
            result = await session.scalars(
                GcnEventExtraction.select(
                    session.user_or_token,
                    options=[selectinload(GcnEventExtraction.gcnevent)],
                )
                .where(
                    GcnEventExtraction.dateobs.in_(sa.select(recent_events.c.dateobs))
                )
                .order_by(GcnEventExtraction.created_at.desc())
            )
            extractions = []
            for extraction in result.unique().all():
                data = extraction.data or {}
                event: GcnEvent | None = extraction.gcnevent
                extractions.append(
                    {
                        "id": extraction.id,
                        "origin": extraction.origin,
                        "circular_id": extraction.circular_id,
                        "created_at": extraction.created_at,
                        "circular_created_at": extraction.circular_created_at,
                        "dateobs": extraction.dateobs,
                        "event_aliases": list(event.aliases or []) if event else [],
                        # A summary rather than the whole record: the widget shows
                        # what was found, and the full JSON lives on the event page.
                        "summary": _summarize(data),
                    }
                )
            return self.success(data=extractions)


def _summarize(data: dict) -> dict:
    """Counts and headline values a reader can scan without opening the record."""
    photometry = data.get("photometry") or []
    event = data.get("event") or {}
    name = event.get("event_name")
    if isinstance(name, list):
        name = name[0] if name else None
    redshift = (data.get("redshift") or {}).get("redshift")
    classification = (data.get("classification") or {}).get("classification")
    localization = data.get("localization") or {}
    bandpasses = sorted(
        {row.get("bandpass") for row in photometry if row.get("bandpass")}
    )
    return {
        "event_name": name,
        "n_photometry": len(photometry),
        "n_detections": sum(1 for row in photometry if row.get("is_detection")),
        "bandpasses": bandpasses,
        "redshift": redshift,
        "classification": classification,
        "ra": localization.get("ra"),
        "dec": localization.get("dec"),
    }
