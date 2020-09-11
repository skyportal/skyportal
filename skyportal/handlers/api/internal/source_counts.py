import datetime
from sqlalchemy import func
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, Source

default_prefs = {'sinceDaysAgo': 7}


class SourceCountHandler(BaseHandler):
    @auth_or_token
    def get(self):
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        source_count_prefs = user_prefs.get('sourceCounts', {})
        source_count_prefs = {**default_prefs, **source_count_prefs}

        since_days_ago = int(source_count_prefs['sinceDaysAgo'])

        cutoff_day = (
            datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        ).isoformat()

        q = (
            DBSession.query(func.count(Source.obj_id).label('count'))
            .filter(
                Source.group_id.in_([g.id for g in self.current_user.accessible_groups])
            )
            .filter(Source.created_at >= cutoff_day)
        )
        result = q.first()[0]
        data = {"count": result, "since_days_ago": since_days_ago}
        return self.success(data=data)
