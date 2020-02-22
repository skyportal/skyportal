import datetime
from sqlalchemy import func, desc
import tornado.web
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import (
    DBSession, Source, SourceView, GroupSource
)


class SourceViewsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        prefs = (self.current_user.preferences if
                 hasattr(self.current_user, 'preferences') and
                 self.current_user.preferences is not None else {})
        if 'topSources' in prefs and 'maxNumSources' in prefs['topSources']:
            max_num_sources = int(prefs['topSources']['maxNumSources'])
        else:
            max_num_sources = 10
        if 'topSources' in prefs and 'sinceDaysAgo' in prefs['topSources']:
            since_days_ago = int(prefs['topSources']['sinceDaysAgo'])
        else:
            since_days_ago = 30
        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        q = (DBSession.query(func.count(SourceView.source_id).label('views'),
                             SourceView.source_id).group_by(SourceView.source_id)
             .filter(SourceView.source_id.in_(DBSession.query(
                 GroupSource.source_id).filter(GroupSource.group_id.in_(
                     [g.id for g in self.current_user.groups]))))
             .filter(SourceView.created_at >= cutoff_day)
             .order_by(desc('views')).limit(max_num_sources))
        return self.success(data={'sourceViews': q.all()})

    @tornado.web.authenticated
    def post(self, source_id):
        # Ensure user has access to source
        s = Source.get_if_owned_by(source_id, self.current_user)
        # This endpoint will only be hit by front-end, so this will never be a token
        register_source_view(source_id=source_id,
                             username_or_token_id=self.current_user.username,
                             is_token=False)
        return self.success()


def register_source_view(source_id, username_or_token_id, is_token):
    sv = SourceView(source_id=source_id,
                    username_or_token_id=username_or_token_id,
                    is_token=is_token)
    DBSession.add(sv)
    DBSession.commit()
