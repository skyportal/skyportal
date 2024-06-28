import datetime

import sqlalchemy as sa
from sqlalchemy import func, desc

from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import User, Source, Candidate


default_prefs = {'maxNumSavers': 100, 'sinceDaysAgo': 7, 'candidatesOnly': True}


class SourceSaverHandler(BaseHandler):
    @classmethod
    def get_top_source_savers(cls, current_user, session, user_options):
        user_prefs = getattr(current_user, 'preferences', None) or {}
        top_savers_prefs = user_prefs.get('topSavers', {})
        top_savers_prefs = {**default_prefs, **top_savers_prefs, **user_options}

        max_num_savers = int(top_savers_prefs['maxNumSavers'])
        since_days_ago = float(top_savers_prefs['sinceDaysAgo'])
        cutoff_day = datetime.datetime.utcnow() - datetime.timedelta(
            days=since_days_ago
        )

        stmt = Source.select(
            session.user_or_token,
            columns=[
                func.count(sa.distinct(Source.obj_id)).label('saves'),
                Source.saved_by_id,
            ],
        ).where(Source.saved_at >= cutoff_day)

        if top_savers_prefs['candidatesOnly']:
            stmt = stmt.where(
                sa.exists(
                    sa.select(Candidate.obj_id).where(Candidate.obj_id == Source.obj_id)
                )
            )

        stmt = (
            stmt.group_by(Source.saved_by_id)
            .order_by(desc('saves'))
            .limit(max_num_savers)
        )

        results = session.execute(stmt).all()

        return results

    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve users saving candidates
        tags:
          - sources
        parameters:
          - in: query
            name: maxNumSavers
            required: false
            schema:
              type: integer
          - in: query
            name: sinceDaysAgo
            required: false
            schema:
              type: integer
          - in: query
            name: candidatesOnly
            required: false
            schema:
              type: boolean
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfUsers
          400:
            content:
              application/json:
                schema: Error
        """
        max_num_savers = self.get_query_argument('maxNumSavers', None)
        since_days_ago = self.get_query_argument('sinceDaysAgo', None)
        candidates_only = self.get_query_argument('candidatesOnly', None)

        user_options = {}
        if max_num_savers is not None:
            user_options['maxNumSavers'] = max_num_savers
        if since_days_ago is not None:
            user_options['sinceDaysAgo'] = since_days_ago
        if candidates_only is not None:
            user_options['candidatesOnly'] = candidates_only

        with self.Session() as session:
            try:
                query_results = SourceSaverHandler.get_top_source_savers(
                    self.current_user, session, user_options
                )
                savers = []
                for rank, (saved, user_id) in enumerate(query_results):
                    s = session.scalars(
                        User.select(session.user_or_token).where(User.id == user_id)
                    ).first()
                    savers.append(
                        {
                            'rank': rank + 1,
                            'author': {**s.to_dict(), "gravatar_url": s.gravatar_url},
                            'saves': saved,
                        }
                    )

                return self.success(data=savers)
            except Exception as e:
                return self.error(f'Failed to fetch source savers: {e}')
