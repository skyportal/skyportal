from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, ObservingRun, ClassicalAssignment, Obj, Thumbnail
from ...schema import ObservingRunPost, ObservingRunGet, ObservingRunGetWithAssignments


class ObservingRunHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Add a new observing run
        requestBody:
          content:
            application/json:
              schema: ObservingRunPost
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New Observing Run ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        try:
            rund = ObservingRunPost.load(data)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )

        run = ObservingRun(**rund)
        run.owner_id = self.associated_user_object.id

        DBSession().add(run)
        DBSession().commit()

        return self.success(data={"id": run.id})

    @auth_or_token
    def get(self, run_id=None):
        """
        ---
        single:
          description: Retrieve an observing run
          parameters:
            - in: path
              name: run_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleObservingRunGetWithAssignments
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all observing runs
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfObservingRunGets
            400:
              content:
                application/json:
                  schema: Error
        """
        if run_id is not None:
            run = (
                DBSession()
                .query(ObservingRun)
                .options(
                    joinedload(ObservingRun.assignments)
                    .joinedload(ClassicalAssignment.obj)
                    .joinedload(Obj.thumbnails)
                    .joinedload(Thumbnail.photometry),
                    joinedload(ObservingRun.assignments).joinedload(
                        ClassicalAssignment.requester
                    ),
                    joinedload(ObservingRun.assignments)
                    .joinedload(ClassicalAssignment.obj)
                    .joinedload(Obj.comments),
                )
                .filter(ObservingRun.id == run_id)
                .first()
            )

            if run is None:
                return self.error(
                    f"Could not load observing run {run_id}", data={"run_id": run_id}
                )
            # order the assignments by ra
            run.assignments = sorted(run.assignments, key=lambda a: a.obj.ra)

            # filter out the assignments of objects that are not visible to
            # the user
            run.assignments = list(
                filter(lambda a: a.obj.is_owned_by(self.current_user), run.assignments)
            )

            for assignment in run.assignments:
                assignment.obj.comments = sorted(
                    assignment.obj.comments, key=lambda c: c.modified, reverse=True
                )

            data = ObservingRunGetWithAssignments.dump(run)
            data['assignments'] = [a.to_dict() for a in data['assignments']]

            # calculate when the targets rise and set
            for d, a in zip(data['assignments'], run.assignments):
                d['rise_time_utc'] = a.rise_time.isot
                d['set_time_utc'] = a.set_time.isot

            return self.success(data=data)
        runs = ObservingRun.query.all()
        data = ObservingRunGet.dump(runs, many=True)
        out = sorted(data, key=lambda d: d['ephemeris']['sunrise_utc'])
        return self.success(data=out)

    @permissions(['Upload data'])
    def put(self, run_id):
        """
        ---
        description: Update observing run
        parameters:
          - in: path
            name: run_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: ObservingRunPost
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

        data = self.get_json()
        run_id = int(run_id)
        is_superadmin = 'System admin' in [a.id for a in self.current_user.acls]

        orun = ObservingRun.query.get(run_id)

        current_user_id = self.associated_user_object.id

        if orun.owner_id != current_user_id and not is_superadmin:
            return self.error(
                'Only the owner of an observing run can modify the run.'
            )
        try:
            new_params = ObservingRunPost.load(data, partial=True)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )

        for param in new_params:
            setattr(orun, param, new_params[param])

        DBSession().add(orun)
        DBSession().commit()
        return self.success()

    @permissions(['Upload data'])
    def delete(self, run_id):
        """
        ---
        description: Delete an observing run
        parameters:
          - in: path
            name: run_id
            required: true
            schema:
              type: integer
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
        run_id = int(run_id)
        is_superadmin = 'System admin' in [a.id for a in self.current_user.acls]

        run = ObservingRun.query.get(run_id)

        current_user_id = self.associated_user_object.id

        if run.owner_id != current_user_id and not is_superadmin:
            return self.error(
                'Only the owner of an observing run can modify ' 'the run.'
            )

        DBSession().query(ObservingRun).filter(ObservingRun.id == run_id).delete()
        DBSession().commit()

        return self.success()
