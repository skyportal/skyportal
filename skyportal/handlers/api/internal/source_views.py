import datetime
from sqlalchemy import func, desc
import tornado.web
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import (
    DBSession, Obj, Source, SourceView
)


default_prefs = {
    'maxNumSources': 10,
    'sinceDaysAgo': 7
}


class SourceViewsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        top_sources_prefs = user_prefs.get('topSources', {})
        top_sources_prefs = {**default_prefs, **top_sources_prefs}

        max_num_sources = int(top_sources_prefs['maxNumSources'])
        since_days_ago = int(top_sources_prefs['sinceDaysAgo'])

        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        q = (DBSession.query(func.count(SourceView.obj_id).label('views'),
                             SourceView.obj_id).group_by(SourceView.obj_id)
             .filter(SourceView.obj_id.in_(DBSession.query(
                 Source.obj_id).filter(Source.group_id.in_(
                     [g.id for g in self.current_user.accessible_groups]))))
             .filter(SourceView.created_at >= cutoff_day)
             .order_by(desc('views')).limit(max_num_sources))
        return self.success(data=q.all())

    @tornado.web.authenticated
    def post(self, obj_id):
        # Ensure user has access to source
        s = Source.get_obj_if_owned_by(obj_id, self.current_user)
        # This endpoint will only be hit by front-end, so this will never be a token
        register_source_view(obj_id=obj_id,
                             username_or_token_id=self.current_user.username,
                             is_token=False)
        return self.success()


def register_source_view(obj_id, username_or_token_id, is_token):
    sv = SourceView(obj_id=obj_id,
                    username_or_token_id=username_or_token_id,
                    is_token=is_token)
    DBSession.add(sv)
    DBSession.commit()
