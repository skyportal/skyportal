import datetime
import sqlalchemy as sa
from sqlalchemy import func
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import Source

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

        with self.Session() as session:
            stmt = Source.select(session.user_or_token).where(
                Source.created_at >= cutoff_day
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            result = session.execute(count_stmt).scalar()
            data = {"count": result, "sinceDaysAgo": since_days_ago}
            return self.success(data=data)
