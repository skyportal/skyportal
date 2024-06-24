import sqlalchemy as sa

from baselayer.app.models import DBSession
from ...models.public_pages.public_release import PublicRelease

from ..base import BaseHandler


class ReleaseHandler(BaseHandler):
    def get(self):
        """
        Get all public releases
        :return: HTML page with all public releases
        """
        with DBSession() as session:
            releases = session.scalars(
                sa.select(PublicRelease).order_by(PublicRelease.name.asc())
            ).all()
            return self.render(
                "public_pages/releases/releases_template.html",
                releases=releases,
            )
