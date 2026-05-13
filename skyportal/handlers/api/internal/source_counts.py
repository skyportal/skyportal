import datetime

import sqlalchemy as sa
from sqlalchemy import func

from baselayer.app.access import auth_or_token

from ....models import Source
from ...base import BaseHandler

default_prefs = {"sinceDaysAgo": 7}


class SourceCountHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        user_prefs = getattr(self.current_user, "preferences", None) or {}
        source_count_prefs = user_prefs.get("sourceCounts", {})
        source_count_prefs = {**default_prefs, **source_count_prefs}

        since_days_ago = int(source_count_prefs["sinceDaysAgo"])

        # Pass datetime directly rather than isoformat() — psycopg3 binds
        # Python strings as VARCHAR, which Postgres refuses to compare to
        # the timestamp column.
        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)

        async with self.AsyncSession() as session:
            stmt = Source.select(session.user_or_token).where(
                Source.created_at >= cutoff_day
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            result = await session.scalar(count_stmt)
            data = {"count": result, "sinceDaysAgo": since_days_ago}
            return self.success(data=data)
