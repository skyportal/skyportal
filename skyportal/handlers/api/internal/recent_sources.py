from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from collections import defaultdict
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import Obj, Source


default_prefs = {'maxNumSources': 5}


class RecentSourcesHandler(BaseHandler):
    @classmethod
    def get_recent_source_ids(self, current_user):
        user_prefs = getattr(current_user, 'preferences', None) or {}
        recent_sources_prefs = user_prefs.get('recentSources', {})
        recent_sources_prefs = {**default_prefs, **recent_sources_prefs}

        max_num_sources = int(recent_sources_prefs['maxNumSources'])
        query_results = (
            Source.query_records_accessible_by(current_user)
            .filter(Source.active.is_(True))
            .order_by(desc(Source.created_at))
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
        sources_seen = defaultdict(lambda: 1)
        for obj_id in query_results:
            # The recency_index is how current a source row was saved for a given
            # object. If recency_index = 0, this is the most recent time a source
            # was saved; recency_index = 1 is the second-latest time the source
            # was saved, etc.
            recency_index = 0
            if obj_id in sources_seen:
                recency_index = sources_seen[obj_id]
                sources_seen[obj_id] += 1

            s = Obj.get_if_accessible_by(
                obj_id,
                self.current_user,
                options=[joinedload(Obj.thumbnails)],
            )

            # Get the entry in the Source table to get the accurate saved_at time
            source_entry = (
                Source.query_records_accessible_by(self.current_user)
                .filter(Source.obj_id == obj_id)
                .order_by(desc(Source.created_at))
                .offset(recency_index)
                .first()
            )

            info = first_thumbnail_info(s.thumbnails)
            sources.append(
                {
                    'obj_id': s.id,
                    'ra': s.ra,
                    'dec': s.dec,
                    'created_at': source_entry.created_at,
                    'public_url': info[0],
                    'is_grayscale': info[1],
                    'classifications': s.classifications,
                    'recency_index': recency_index,
                }
            )

        for source in sources:
            num_times_seen = sources_seen[source["obj_id"]]
            # If this source was saved multiple times recently, and this is not
            # the oldest instance of an object being saved (highest recency_index)
            if num_times_seen > 1 and source["recency_index"] != num_times_seen - 1:
                source["resaved"] = True
            else:
                source["resaved"] = False
            # Delete bookkeeping recency_index key
            del source["recency_index"]

        self.verify_and_commit()
        return self.success(data=sources)


def first_thumbnail_info(thumbnails):
    infos = [
        (t.public_url, t.is_grayscale)
        for t in sorted(thumbnails, key=lambda t: tIndex(t.type))
    ]
    return infos[0] if infos else ("", False)


def tIndex(t):
    thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8']
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
