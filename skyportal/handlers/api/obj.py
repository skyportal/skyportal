import sqlalchemy as sa
from sqlalchemy import func

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import Comment, Obj, PhotometricSeries, Photometry, Spectrum

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

            stmt = Spectrum.select(session.user_or_token).where(
                Spectrum.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_spectrum = session.execute(count_stmt).scalar()
            if total_spectrum > 0:
                return self.error(
                    f"Please remove all associated spectra to object with ID {obj_id} before removing."
                )

            stmt = Photometry.select(session.user_or_token).where(
                Photometry.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_photometry = session.execute(count_stmt).scalar()
            if total_photometry > 0:
                return self.error(
                    f"Please remove all associated photometry to object with ID {obj_id} before removing."
                )

            stmt = PhotometricSeries.select(session.user_or_token).where(
                PhotometricSeries.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_photometric_series = session.execute(count_stmt).scalar()
            if total_photometric_series > 0:
                return self.error(
                    f"Please remove all associated photometric series to object with ID {obj_id} before removing."
                )

            stmt = Comment.select(session.user_or_token).where(Comment.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_comments = session.execute(count_stmt).scalar()
            if total_comments > 0:
                return self.error(
                    f"Please remove all associated comments on object with ID {obj_id} before removing."
                )

            session.delete(obj)
            session.commit()
            return self.success()
