from sqlalchemy.orm import joinedload
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import GcnEvent

default_prefs = {'maxNumGcnEvents': 10}


class RecentGcnEventsHandler(BaseHandler):
    @auth_or_token
    def get(self):
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
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        recent_events_prefs = user_prefs.get('recentGcnEvents', {})
        recent_events_prefs = {**default_prefs, **recent_events_prefs}

        max_num_events = (
            int(recent_events_prefs['maxNumEvents'])
            if 'maxNumEvents' in recent_events_prefs
            else 5
        )
        with self.Session() as session:
            q = (
                session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                        options=[
                            joinedload(GcnEvent.localizations),
                            joinedload(GcnEvent.gcn_triggers),
                        ],
                    )
                    .order_by(GcnEvent.dateobs.desc())
                    .limit(max_num_events)
                )
                .unique()
                .all()
            )
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
