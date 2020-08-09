import datetime
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
import tornado.web
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import (
    DBSession, Obj, Event, EventView
)


default_prefs = {
    'maxNumEvents': 10,
    'sinceDaysAgo': 1000
}


class EventViewsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        top_events_prefs = user_prefs.get('topEvents', {})
        top_events_prefs = {**default_prefs, **top_events_prefs}

        max_num_events = int(top_events_prefs['maxNumEvents'])
        since_days_ago = int(top_events_prefs['sinceDaysAgo'])

        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        print(cutoff_day)

        q = (DBSession.query(func.count(EventView.event_id).label('views'),
                             EventView.event_id).group_by(EventView.event_id)
             .filter(EventView.created_at >= cutoff_day)
             .order_by(desc('views')).limit(max_num_events))

        q = Event.query

        events = []
        for event in q.all():
            dateobs = event.dateobs
            tags = [_ for _ in event.tags]
            localizations = [_.localization_name for _ in event.localizations]
            events.append({'localizations': localizations, 'dateobs': dateobs,
                            'tags': tags})    

        print(events)

        return self.success(data=events)

    @tornado.web.authenticated
    def post(self, obj_id):
        # Ensure user has access to event
        s = Event.get_obj_if_owned_by(obj_id, self.current_user)
        # This endpoint will only be hit by front-end, so this will never be a token
        register_event_view(obj_id=obj_id,
                            username_or_token_id=self.current_user.username,
                            is_token=False)
        return self.success()


def register_event_view(event_id, username_or_token_id, is_token):
    sv = EventView(event_id=event_id,
                   username_or_token_id=username_or_token_id,
                   is_token=is_token)
    DBSession.add(sv)
    DBSession.commit()

def first_public_url(thumbnails):
    urls = [t.public_url for t in sorted(thumbnails, key=lambda t: tIndex(t))]
    return urls[0] if urls else ""

def tIndex(t):
    thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8'] 
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
