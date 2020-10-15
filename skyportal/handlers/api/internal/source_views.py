import datetime
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
import tornado.web
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, Obj, Source, SourceView


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
            DBSession.query(
                func.count(SourceView.obj_id).label('views'), SourceView.obj_id
            )
            .group_by(SourceView.obj_id)
            .filter(
                SourceView.obj_id.in_(
                    DBSession.query(Source.obj_id).filter(
                        Source.group_id.in_(
                            [g.id for g in current_user.accessible_groups]
                        )
                    )
                )
            )
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
            s = Source.get_obj_if_owned_by(  # Returns Source.obj
                obj_id,
                self.current_user,
                options=[joinedload(Source.obj).joinedload(Obj.thumbnails)],
            )
            public_url = first_public_url(s.thumbnails)
            sources.append(
                {
                    'obj_id': s.id,
                    'views': view,
                    'ra': s.ra,
                    'dec': s.dec,
                    'public_url': public_url,
                    'classifications': s.classifications,
                }
            )

        return self.success(data=sources)

    @tornado.web.authenticated
    def post(self, obj_id):
        # Ensure user has access to source
        Source.get_obj_if_owned_by(obj_id, self.current_user)
        # This endpoint will only be hit by front-end, so this will never be a token
        register_source_view(
            obj_id=obj_id,
            username_or_token_id=self.current_user.username,
            is_token=False,
        )
        self.push_all(action="skyportal/FETCH_TOP_SOURCES")
        return self.success()


def register_source_view(obj_id, username_or_token_id, is_token):
    sv = SourceView(
        obj_id=obj_id, username_or_token_id=username_or_token_id, is_token=is_token
    )
    DBSession.add(sv)
    DBSession.commit()


def first_public_url(thumbnails):
    urls = [t.public_url for t in sorted(thumbnails, key=lambda t: tIndex(t.type))]
    return urls[0] if urls else ""


def tIndex(t):
    thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8']
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
