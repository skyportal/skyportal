import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ....models import Group, PaperCornerCache, Source
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
        sources = cfg["paper_corner.sources"]
        if obj_id is not None and obj_id not in sources:
            return self.success(data=disabled)

        async with self.AsyncSession() as session:
            visible = (
                Source.select(session.user_or_token, columns=[Source.obj_id])
                .where(
                    Source.group_id
                    == sa.select(Group.id)
                    .where(Group.name == cfg["misc.public_group_name"])
                    .scalar_subquery(),
                    Source.active.is_(True),
                    Source.obj_id.in_(list(sources) if obj_id is None else [obj_id]),
                )
                .distinct()
                .subquery()
            )
            rows = (
                await session.execute(
                    sa.select(visible.c.obj_id, PaperCornerCache.c.matches).outerjoin(
                        PaperCornerCache, PaperCornerCache.c.obj_id == visible.c.obj_id
                    )
                )
            ).all()

        if obj_id is not None and not rows:
            return self.success(data=disabled)
        matches = (
            (source_id, match)
            for source_id, records in rows
            for match in records or []
            if match["designation"] in sources[source_id]
        )
        return self.success(
            data={
                "enabled": True,
                "pending": any(records is None for _, records in rows),
                "papers": collect_papers(matches, 5 if obj_id is None else 25),
            }
        )
