from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ....models import GcnEvent, GcnEventExtraction
from ...base import BaseHandler

default_prefs = {"maxNumExtractions": 10}


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
        prefs = {**default_prefs, **user_prefs.get("recentGcnExtractions", {})}
        try:
            max_num = int(prefs["maxNumExtractions"])
        except (TypeError, ValueError):
            max_num = default_prefs["maxNumExtractions"]

        async with self.AsyncSession() as session:
            # The event's dateobs and aliases are rendered beside each extraction,
            # so eager-load the event rather than lazy-loading inside the loop.
            result = await session.scalars(
                GcnEventExtraction.select(
                    session.user_or_token,
                    options=[selectinload(GcnEventExtraction.gcnevent)],
                )
                .order_by(GcnEventExtraction.created_at.desc())
                .limit(max_num)
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
