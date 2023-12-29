import datetime
from sqlalchemy import func, desc
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import User, Source


default_prefs = {'maxNumSavers': 10, 'sinceDaysAgo': 7}


class SourceSaverHandler(BaseHandler):
    @classmethod
    def get_top_source_savers(self, current_user, session):
        user_prefs = getattr(current_user, 'preferences', None) or {}
        top_savers_prefs = user_prefs.get('topSavers', {})
        top_savers_prefs = {**default_prefs, **top_savers_prefs}

        max_num_savers = int(top_savers_prefs['maxNumSavers'])
        since_days_ago = int(top_savers_prefs['sinceDaysAgo'])
        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)

        results = session.execute(
            User.select(
                session.user_or_token,
                columns=[
                    func.count(Source.id).label('saves'),
                    User.id,
                ],
            )
            .group_by(User.id)
            .where(Source.saved_by_id == User.id)
            .where(Source.saved_at >= cutoff_day)
            .order_by(desc('saves'))
            .limit(max_num_savers)
        ).all()

        return results

    @auth_or_token
    def get(self):

        with self.Session() as session:
            query_results = SourceSaverHandler.get_top_source_savers(
                self.current_user, session
            )
            savers = []
            for saved, user_id in query_results:
                s = session.scalars(
                    User.select(session.user_or_token).where(User.id == user_id)
                ).first()
                savers.append(
                    {
                        'author': {**s.to_dict(), "gravatar_url": s.gravatar_url},
                        'saves': saved,
                    }
                )

            return self.success(data=savers)
