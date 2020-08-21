from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, Obj, Source


default_prefs = {'maxNumSources': 10}


class RecentSourcesHandler(BaseHandler):
    @auth_or_token
    def get(self):
        user_prefs = getattr(self.current_user, 'preferences', None) or {}
        recent_sources_prefs = user_prefs.get('recentSources', {})
        recent_sources_prefs = {**default_prefs, **recent_sources_prefs}

        max_num_sources = int(recent_sources_prefs['maxNumSources'])

        query_results = (
            Obj.query.filter(
                Obj.id.in_(
                    DBSession()
                    .query(Source.obj_id)
                    .filter(
                        Source.group_id.in_([g.id for g in self.current_user.groups])
                    )
                )
            )
            .order_by(desc('created_at'))
            .limit(max_num_sources)
        ).all()

        sources = []
        for obj in query_results:
            s = Source.get_obj_if_owned_by(  # Returns Source.obj
                obj.id,
                self.current_user,
                options=[joinedload(Source.obj).joinedload(Obj.thumbnails)],
            )
            public_url = first_public_url(s.thumbnails)
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


def first_public_url(thumbnails):
    urls = [t.public_url for t in sorted(thumbnails, key=lambda t: tIndex(t))]
    return urls[0] if urls else ""


def tIndex(t):
    thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8']
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
