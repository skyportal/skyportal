import datetime
from collections import defaultdict

import sqlalchemy as sa
import tornado.web
from sqlalchemy import desc, func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ....models import Obj, ObjTag, Source, SourceView, serialize_obj_tag
from ....utils.data_access import (
    accessible_group_ids_async,
    team_scoped_group_ids,
)
from ....utils.naive_datetime import utcnow_naive
from ...base import BaseHandler

default_prefs = {
    "maxNumSources": 10,
    "sinceDaysAgo": 7,
}


class SourceViewsHandler(BaseHandler):
    @classmethod
    async def get_top_source_views_and_ids(
        cls, current_user, session, team_group_ids=None
    ):
        user_prefs = getattr(current_user, "preferences", None) or {}
        top_sources_prefs = user_prefs.get("topSources", {})
        top_sources_prefs = {**default_prefs, **top_sources_prefs}

        max_num_sources = int(top_sources_prefs["maxNumSources"])
        since_days_ago = float(top_sources_prefs["sinceDaysAgo"])
        cutoff_day = utcnow_naive() - datetime.timedelta(days=since_days_ago)
        stmt = (
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
        )
        if team_group_ids is not None:
            # SourceView carries no group; scope to objs saved to the team's groups.
            stmt = stmt.where(
                SourceView.obj_id.in_(
                    sa.select(Source.obj_id).where(Source.group_id.in_(team_group_ids))
                )
            )
        stmt = stmt.order_by(desc("views")).limit(max_num_sources)
        result = await session.execute(stmt)
        return result.all()

    @auth_or_token
    async def get(self):
        async with self.AsyncSession() as session:
            user_group_ids = set(
                await accessible_group_ids_async(session.user_or_token, session)
            )
            try:
                team_group_ids = await team_scoped_group_ids(
                    session,
                    self.current_user,
                    self.get_query_argument("teamID", None),
                    user_group_ids,
                )
            except ValueError as e:
                return self.error(str(e))
            query_results = await SourceViewsHandler.get_top_source_views_and_ids(
                self.current_user, session, team_group_ids=team_group_ids
            )
            tags_result = await session.scalars(
                ObjTag.select(session.user_or_token)
                .options(
                    selectinload(ObjTag.objtagoption),
                    selectinload(ObjTag.groups),
                )
                .where(ObjTag.obj_id.in_(list({obj_id for _, obj_id in query_results})))
            )
            tags = tags_result.all()
            tags = [serialize_obj_tag(tag, user_group_ids) for tag in tags]
            # make it a hashmap of obj_id to tags
            tags_dict = defaultdict(list)
            for tag in tags:
                tags_dict[tag["obj_id"]].append(tag)

            sources = []
            for view, obj_id in query_results:
                s = await session.scalar(
                    Obj.select(
                        session.user_or_token,
                        options=[
                            selectinload(Obj.thumbnails),
                            selectinload(Obj.classifications),
                        ],
                    ).where(Obj.id == obj_id)
                )
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
                        "tags": tags_dict.get(s.id, []),
                    }
                )

            return self.success(data=sources)

    @tornado.web.authenticated
    async def post(self, obj_id: str):
        async with self.AsyncSession() as session:
            sv = SourceView(
                obj_id=obj_id,
                username_or_token_id=self.current_user.username,
                is_token=False,
            )
            session.add(sv)
            await session.commit()
            return self.success()


def t_index(t):
    thumbnail_order = [
        "new",
        "ref",
        "sub",
        "sdss",
        "dr8",
        "ps1",
        "sm",
        "hst",
        "chandra",
        "jwst",
    ]
    return thumbnail_order.index(t) if t in thumbnail_order else len(thumbnail_order)
