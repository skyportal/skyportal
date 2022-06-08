import sqlalchemy as sa
from ..base import BaseHandler
from ...models import (
    DBSession,
    Obj,
    Photometry,
    PhotStat,
)
from baselayer.app.access import permissions, auth_or_token


class PhotStatHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        description: retrieve the PhotStat associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
        responses:
          200:
            content:
              application/json:
                schema: PhotStat
          400:
              content:
                application/json:
                  schema: Error

        """
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error(f'Cannot find source with id "{obj_id}". ')

        with DBSession() as session:
            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()

            if phot_stat is None:
                return self.error(
                    f'Could not find a PhotStat for object with id "{obj_id}". '
                )

            stmt = (
                sa.select(Photometry)
                .where(Photometry.obj_id == obj_id)
                .order_by(Photometry.created_at.desc())
            )
            last_photometry = session.scalars(stmt).first()
            if last_photometry:
                phot_stat.last_phot_add_time = last_photometry.created_at
            else:
                phot_stat.last_phot_add_time = None

        return self.success(data=phot_stat)

    @permissions(['system admin'])
    def post(self, obj_id=None):
        """
        ---
        description: create a new PhotStat to be associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Success'
          400:
              content:
                application/json:
                  schema: Error

        """
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error(f'Cannot find source with id "{obj_id}". ')

        with DBSession() as session:
            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()
            if phot_stat is not None:
                return self.error(
                    f'PhotStat for object with id "{obj_id}" already exists. '
                )

            stmt = sa.select(Photometry).where(Photometry.obj_id == obj_id)
            photometry = session.scalars(stmt).all()

            phot_stat = PhotStat(obj_id=obj_id)
            phot_stat.full_update(photometry)
            session.add(phot_stat)
            self.verify_and_commit()

        return self.success()

    @permissions(['system admin'])
    def put(self, obj_id=None):
        """
        ---
        description: create or update the PhotStat associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Success'
          400:
              content:
                application/json:
                  schema: Error

        """
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error(f'Cannot find source with id "{obj_id}". ')

        with DBSession() as session:
            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()
            if phot_stat is None:
                phot_stat = PhotStat()

            stmt = sa.select(Photometry).where(Photometry.obj_id == obj_id)
            photometry = session.scalars(stmt).all()
            phot_stat.full_update(photometry)
            session.add(phot_stat)
            self.verify_and_commit()

        return self.success()

    @permissions(['system admin'])
    def delete(self, obj_id=None):
        """
        ---
        description: delete the PhotStat associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Success'
          400:
              content:
                application/json:
                  schema: Error
        """
        obj = Obj.get_if_accessible_by(obj_id, self.current_user)
        if obj is None:
            return self.error(f'Cannot find source with id "{obj_id}". ')

        with DBSession() as session:
            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()
            if phot_stat is None:
                return self.error(
                    f'Could not find a PhotStat for object with id "{obj_id}". '
                )
            session.delete(phot_stat)
            self.verify_and_commit()

        return self.success()
