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
          - gcnevents
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
        q = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[joinedload(GcnEvent.localizations)],
            )
            .order_by(GcnEvent.dateobs.desc())
            .limit(max_num_events)
        )

        events = []
        for event in q.all():
            events.append({**event.to_dict(), "tags": event.tags})

        return self.success(data=events)
