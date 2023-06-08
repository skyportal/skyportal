import sqlalchemy as sa
from sqlalchemy import func

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    Annotation,
    Classification,
    Comment,
    Obj,
    PhotometricSeries,
    Photometry,
    Spectrum,
    SourcesConfirmedInGCN,
)

_, cfg = load_env()


class ObjHandler(BaseHandler):
    @auth_or_token  # ACLs will be checked below based on configs
    def delete(self, obj_id):
        """
        ---
        description: Delete an Obj
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token, mode='delete').where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            stmt = sa.select(Annotation).where(Annotation.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_annotations = session.execute(count_stmt).scalar()
            if total_annotations > 0:
                return self.error(
                    f"Please remove all associated annotations from object with ID {obj_id} before removing."
                )

            stmt = sa.select(Spectrum).where(Spectrum.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_spectrum = session.execute(count_stmt).scalar()
            if total_spectrum > 0:
                return self.error(
                    f"Please remove all associated spectra from object with ID {obj_id} before removing."
                )

            stmt = sa.select(Photometry).where(Photometry.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_photometry = session.execute(count_stmt).scalar()
            if total_photometry > 0:
                return self.error(
                    f"Please remove all associated photometry from object with ID {obj_id} before removing."
                )

            stmt = sa.select(PhotometricSeries).where(
                PhotometricSeries.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_photometric_series = session.execute(count_stmt).scalar()
            if total_photometric_series > 0:
                return self.error(
                    f"Please remove all associated photometric series from object with ID {obj_id} before removing."
                )

            stmt = sa.select(Comment).where(Comment.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_comments = session.execute(count_stmt).scalar()
            if total_comments > 0:
                return self.error(
                    f"Please remove all associated comments on object with ID {obj_id} before removing."
                )

            stmt = sa.select(Classification).where(Classification.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_classifications = session.execute(count_stmt).scalar()
            if total_classifications > 0:
                return self.error(
                    f"Please remove all associated classifications on object with ID {obj_id} before removing."
                )

            stmt = sa.select(SourcesConfirmedInGCN).where(
                SourcesConfirmedInGCN.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_sources_in_gcn = session.execute(count_stmt).scalar()
            if total_sources_in_gcn > 0:
                return self.error(
                    f"Please remove all associated sources in gcns associated with the object with ID {obj_id} before removing."
                )

            session.delete(obj)
            session.commit()
            return self.success()
