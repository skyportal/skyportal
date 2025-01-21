import datetime

import tornado.web
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token

from ....models import Obj, SourceView
from ...base import BaseHandler

default_prefs = {"maxNumSources": 10, "sinceDaysAgo": 7}


class SourceViewsHandler(BaseHandler):
    @classmethod
    def get_top_source_views_and_ids(cls, current_user, session):
        user_prefs = getattr(current_user, "preferences", None) or {}
        top_sources_prefs = user_prefs.get("topSources", {})
        top_sources_prefs = {**default_prefs, **top_sources_prefs}

        max_num_sources = int(top_sources_prefs["maxNumSources"])
        since_days_ago = float(top_sources_prefs["sinceDaysAgo"])
        cutoff_day = datetime.datetime.utcnow() - datetime.timedelta(
            days=since_days_ago
        )
        results = session.execute(
            SourceView.select(
                session.user_or_token,
                columns=[
                    func.count(SourceView.obj_id).label("views"),
                    SourceView.obj_id,
                ],
            )
            .group_by(SourceView.obj_id)
            .filter(
                SourceView.created_at >= cutoff_day,
                SourceView.is_token.is_(False),
            )
            .order_by(desc("views"))
            .limit(max_num_sources)
        ).all()

        return results

    @auth_or_token
    def get(self):
        with self.Session() as session:
            query_results = SourceViewsHandler.get_top_source_views_and_ids(
                self.current_user, session
            )
            sources = []
            for view, obj_id in query_results:
                s = session.scalars(
                    Obj.select(
                        session.user_or_token, options=[joinedload(Obj.thumbnails)]
                    ).where(Obj.id == obj_id)
                ).first()
                sources.append(
                    {
                        "obj_id": s.id,
                        "views": view,
                        "ra": s.ra,
                        "dec": s.dec,
                        "thumbnails": [
                            {
                                "type": t.type,
                                "is_grayscale": t.is_grayscale,
                                "public_url": t.public_url,
                            }
                            for t in sorted(s.thumbnails, key=lambda t: t_index(t.type))
                        ],
                        "classifications": s.classifications,
                        "tns_name": s.tns_name,
                    }
                )

            return self.success(data=sources)

    @tornado.web.authenticated
    def post(self, obj_id):
        with self.Session() as session:
            sv = SourceView(
                obj_id=obj_id,
                username_or_token_id=self.current_user.username,
                is_token=False,
            )
            session.add(sv)
            session.commit()
            return self.success()


def t_index(t):
    thumbnail_order = ["new", "ref", "sub", "sdss", "dr8", "ps1"]
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
