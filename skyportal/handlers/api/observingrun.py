from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, ObservingRun
from ...schema import ObservingRunPost


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

        # See bottom of this file for redoc docstring -- moved it there so that
        # it could be made an f-string.

        data = self.get_json()

        try:
            rund = ObservingRunPost.load(data)
        except ValidationError as exc:
            return self.error('Invalid/missing parameters: '
                              f'{exc.normalized_messages()}')

        run = ObservingRun(**rund)

        current_user_id = self.current_user.id if \
            hasattr(self.current_user, 'username') else self.current_user.created_by_id
        run.owner_id = current_user_id

        DBSession().add(run)
        DBSession().commit()

        return self.success(data={"id": run.id})

    @auth_or_token
    def get(self, run_id=None):
        """
        ---
        single:
          description: Retrieve an instrument
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
                  schema: SingleObservingRun
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
                  schema: ArrayOfObservingRuns
            400:
              content:
                application/json:
                  schema: Error
        """
        if run_id is not None:
            run = ObservingRun.query.get(int(run_id))

            if run is None:
                return self.error(f"Could not load observing run {run_id}",
                                  data={"run_id": run_id})
            return self.success(data=run)
        return self.success(data=ObservingRun.query.all())

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

        current_user_id = self.current_user.id if \
            hasattr(self.current_user, 'username') else self.current_user.created_by_id

        if orun.owner_id != current_user_id and not is_superadmin:
            return self.error('Only the owner of an observing run can modify '
                              'the run.')
        try:
            new_params = ObservingRunPost.load(data, partial=True)
        except ValidationError as exc:
            return self.error('Invalid/missing parameters: '
                              f'{exc.normalized_messages()}')

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

        current_user_id = self.current_user.id if \
            hasattr(self.current_user, 'username') else self.current_user.created_by_id

        if run.owner_id != current_user_id and not is_superadmin:
            return self.error('Only the owner of an observing run can modify '
                              'the run.')

        DBSession().query(ObservingRun).filter(
            ObservingRun.id == int(run_id)
        ).delete()
        DBSession().commit()

        return self.success()

