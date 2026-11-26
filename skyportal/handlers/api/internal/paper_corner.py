import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ....models import Obj, PaperCornerCache, Source, tns_paper_sources
from ....utils.paper_corner import collect_papers, paper_corner_enabled
from ...base import BaseHandler

_, cfg = load_env()


class PaperCornerHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        obj_id = self.get_query_argument("objID", None)
        disabled = {"enabled": False, "pending": False, "papers": []}
        if not paper_corner_enabled(cfg):
            return self.success(data=disabled)

        cache = PaperCornerCache.c
        async with self.AsyncSession() as session:
            eligible = tns_paper_sources(
                Source.select(session.user_or_token, columns=[Source.obj_id]),
                cfg["misc.public_group_name"],
            ).add_columns(Obj.tns_name)
            if obj_id is not None:
                eligible = eligible.where(Source.obj_id == obj_id)
            visible = eligible.distinct().subquery()
            stmt = sa.select(visible.c.obj_id, cache.matches).join(
                PaperCornerCache,
                sa.and_(
                    cache.obj_id == visible.c.obj_id,
                    cache.tns_name == visible.c.tns_name,
                ),
                isouter=obj_id is not None,
            )
            if obj_id is None:
                stmt = stmt.where(sa.func.jsonb_array_length(cache.matches) > 0)
            rows = (await session.execute(stmt)).all()

        if obj_id is not None and not rows:
            return self.success(data=disabled)
        matches = (
            (source_id, match) for source_id, records in rows for match in records or []
        )
        return self.success(
            data={
                "enabled": True,
                "pending": any(records is None for _, records in rows),
                "papers": collect_papers(matches, 5 if obj_id is None else 25),
            }
        )
