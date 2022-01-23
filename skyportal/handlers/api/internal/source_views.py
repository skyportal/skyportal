import datetime
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
import tornado.web
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, Obj, SourceView


default_prefs = {'maxNumSources': 10, 'sinceDaysAgo': 7}


class SourceViewsHandler(BaseHandler):
    @classmethod
    def get_top_source_views_and_ids(self, current_user):
        user_prefs = getattr(current_user, 'preferences', None) or {}
        top_sources_prefs = user_prefs.get('topSources', {})
        top_sources_prefs = {**default_prefs, **top_sources_prefs}

        max_num_sources = int(top_sources_prefs['maxNumSources'])
        since_days_ago = int(top_sources_prefs['sinceDaysAgo'])
        cutoff_day = datetime.datetime.now() - datetime.timedelta(days=since_days_ago)
        q = (
            SourceView.query_records_accessible_by(
                current_user,
                columns=[
                    func.count(SourceView.obj_id).label('views'),
                    SourceView.obj_id,
                ],
            )
            .group_by(SourceView.obj_id)
            .filter(SourceView.created_at >= cutoff_day)
            .order_by(desc('views'))
            .limit(max_num_sources)
        )

        return q.all()

    @auth_or_token
    def get(self):
        query_results = SourceViewsHandler.get_top_source_views_and_ids(
            self.current_user
        )
        sources = []
        for view, obj_id in query_results:
            s = Obj.get_if_accessible_by(
                obj_id,
                self.current_user,
                options=[joinedload(Obj.thumbnails)],
            )
            sources.append(
                {
                    'obj_id': s.id,
                    'views': view,
                    'ra': s.ra,
                    'dec': s.dec,
                    'thumbnails': [
                        {
                            "type": t.type,
                            "is_grayscale": t.is_grayscale,
                            "public_url": t.public_url,
                        }
                        for t in sorted(s.thumbnails, key=lambda t: t_index(t.type))
                    ],
                    'classifications': s.classifications,
                }
            )

        return self.success(data=sources)

    @tornado.web.authenticated
    def post(self, obj_id):
        sv = SourceView(
            obj_id=obj_id,
            username_or_token_id=self.current_user.username,
            is_token=False,
        )
        DBSession.add(sv)
        self.verify_and_commit()
        return self.success()


def t_index(t):
    thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8', 'ps1']
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
