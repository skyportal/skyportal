import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import DBSession, GcnPublication
from ...utils.cache import Cache
from ..base import BaseHandler

log = make_log('api/galaxy')
env, cfg = load_env()

Session = scoped_session(sessionmaker())

cache_dir = "cache/publications"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_publications_cache"] * 60,
)

ALLOWED_PUBLICATION_TYPES = ["gcn"]


class PublicationHandler(BaseHandler):
    def get(self, publication_type, publication_id=None, option=None):
        """
        ---
        description: Retrieve all publications
        tags:
          - publications
        responses:
          200:
            content:
              application/json:
                schema: GcnPublication
          400:
            content:
              application/json:
                schema: Error
        """

        if publication_type not in ["gcn"]:
            return self.error(
                f"Invalid publication type {publication_type}, must be one of {ALLOWED_PUBLICATION_TYPES}"
            )

        if publication_id is not None:
            publication_id = int(publication_id)
            cache_key = f"{publication_type}_{publication_id}"
            cached = cache[cache_key]
            if cached is None:
                if Session.registry.has():
                    session = Session()
                else:
                    session = Session(bind=DBSession.session_factory.kw["bind"])

                # if publication_type == "gcn":
                publication = session.scalar(
                    sa.select(GcnPublication).where(GcnPublication.id == publication_id)
                )
                if publication is None:
                    return self.error(
                        f"Could not load GCN publication {publication_id}"
                    )
                if not publication.published:
                    return self.error(
                        f"GCN publication {publication_id} not yet published"
                    )
                publication.generate_publication()
                cached = cache[cache_key]

            data = np.load(cached, allow_pickle=True)
            data = data.item()
            if data['published']:
                if option == "plot":
                    self.set_header("Content-Type", "image/png")
                    return self.write(data['plot'])
                else:
                    self.set_header("Content-Type", "text/html; charset=utf-8")
                    return self.write(data['html'])
            else:
                return self.error(f"Publication {publication_id} not yet published")
        else:
            if Session.registry.has():
                session = Session()
            else:
                session = Session(bind=DBSession.session_factory.kw["bind"])

            if publication_type == "gcn":
                publications = session.scalars(
                    sa.select(GcnPublication)
                    .where(GcnPublication.published is True)
                    .order_by(GcnPublication.dateobs.desc())
                ).all()
                publications = [
                    {
                        **publication.to_dict(),
                        "group_name": publication.group.name,
                    }
                    for publication in publications
                ]
                return self.render(
                    "publications/gcn_publications.html", publications=publications
                )
