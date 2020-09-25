from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, Obj, Source


default_prefs = {'maxNumSources': 5}


class RecentSourcesHandler(BaseHandler):
    @classmethod
    def get_recent_source_ids(self, current_user):
        user_prefs = getattr(current_user, 'preferences', None) or {}
        recent_sources_prefs = user_prefs.get('recentSources', {})
        recent_sources_prefs = {**default_prefs, **recent_sources_prefs}

        max_num_sources = int(recent_sources_prefs['maxNumSources'])
        query_results = (
            DBSession()
            .query(Source)
            .filter(
                Source.obj_id.in_(
                    DBSession()
                    .query(Source.obj_id)
                    .filter(
                        Source.group_id.in_(
                            [g.id for g in current_user.accessible_groups]
                        )
                    )
                )
            )
            .order_by(desc('created_at'))
            .distinct(Source.obj_id, Source.created_at)
            .limit(max_num_sources)
            .all()
        )
        ids = map(lambda src: src.obj_id, query_results)
        return ids

    @auth_or_token
    def get(self):
        query_results = RecentSourcesHandler.get_recent_source_ids(self.current_user)
        sources = []
        for obj_id in query_results:
            s = Source.get_obj_if_owned_by(  # Returns Source.obj
                obj_id,
                self.current_user,
                options=[joinedload(Source.obj).joinedload(Obj.thumbnails)],
            )
            public_url = first_thumbnail_public_url(s.thumbnails)
            sources.append(
                {
                    'obj_id': s.id,
                    'ra': s.ra,
                    'dec': s.dec,
                    'created_at': s.created_at,
                    'public_url': public_url,
                    'classifications': s.classifications,
                }
            )

        return self.success(data=sources)


def first_thumbnail_public_url(thumbnails):
    urls = [t.public_url for t in sorted(thumbnails, key=lambda t: tIndex(t))]
    return urls[0] if urls else ""


def tIndex(t):
    thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8']
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
