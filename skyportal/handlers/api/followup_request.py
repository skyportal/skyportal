import arrow
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (DBSession, Source, FollowupRequest, Token,
                       ClassicalAssignment, ObservingRun)

from ...schema import AssignmentSchema


class AssignmentHandler(BaseHandler):

    @auth_or_token
    def get(self, assignment_id=None):
        """
        ---
        single:
          description: Retrieve an observing run assignment
          parameters:
            - in: path
              name: assignment_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleClassicalAssignment
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all observing run assignments
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfClassicalAssignments
            400:
              content:
                application/json:
                  schema: Error
        """
        if assignment_id is not None:
            assignment = ClassicalAssignment.query.get(int(assignment_id))

            if assignment is None:
                return self.error(f"Could not load assignment {assignment_id}",
                                  data={"assignment_id": assignment_id})
            return self.success(data=assignment)
        return self.success(data=ClassicalAssignment.query.all())

    @auth_or_token
    def post(self):
        """
        ---
        description: Post new target assignment to observing run
        requestBody:
          content:
            application/json:
              schema: AssignmentSchema
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
                              description: New assignment ID
        """

        data = self.get_json()
        try:
            assignment = ClassicalAssignment(**AssignmentSchema.load(data=data))
        except ValidationError as e:
            return self.error(f'Error parsing followup request: '
                              f'"{e.normalized_messages()}"')

        run_id = assignment.run_id
        data['priority'] = assignment.priority.name
        run = ObservingRun.query.get(run_id)
        if run is None:
            return self.error(f'Invalid observing run: "{run_id}"')

        predecessor = ClassicalAssignment.query.filter(
            ClassicalAssignment.obj_id == assignment.obj_id,
            ClassicalAssignment.run_id == run_id
        ).first()

        if predecessor is not None:
            return self.error('Object is already assigned to this run.')

        assignment = ClassicalAssignment(**data)
        source = Source.get_obj_if_owned_by(assignment.obj_id, self.current_user)
        if source is None:
            return self.error(f'Invalid obj_id: "{obj_id}"')

        assignment.requester_id = self.associated_user_object.id
        DBSession().add(assignment)
        DBSession().commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": assignment.obj_id},
        )
        return self.success(data={"id": assignment.id})

    @auth_or_token
    def delete(self, assignment_id):
        """
        ---
        description: Delete assignment.
        parameters:
          - in: path
            name: assignment_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        assignment = ClassicalAssignment.query.get(int(assignment_id))
        user = self.associated_user_object
        delok = "Super admin" in [role.id for role in user.roles] \
                or "Group admin" in [role.id for role in user.roles] \
                or assignment.requester.username == user.username
        if not delok:
            return self.error("Insufficient permissions.")

        DBSession().delete(assignment)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": assignment.obj_id},
        )
        return self.success()


class FollowupRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Submit follow-up request.
        requestBody:
          content:
            application/json:
              schema: FollowupRequestNoID
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
                              description: New follow-up request ID
        """
        data = self.get_json()
        _ = Source.get_obj_if_owned_by(data["obj_id"], self.current_user)
        data["start_date"] = arrow.get(data["start_date"]).datetime
        data["end_date"] = arrow.get(data["end_date"]).datetime
        data["requester_id"] = self.associated_user_object.id
        if isinstance(data["filters"], str):
            data["filters"] = [data["filters"]]
        followup_request = FollowupRequest(**data)
        DBSession().add(followup_request)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": followup_request.obj_id},
        )
        return self.success(data={"id": followup_request.id})

    @auth_or_token
    def put(self, request_id):
        """
        ---
        description: Update a follow-up request
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema: FollowupRequestNoID
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
        followup_request = FollowupRequest.query.get(request_id)
        _ = Source.get_obj_if_owned_by(followup_request.obj_id, self.current_user)
        data = self.get_json()
        data['id'] = request_id
        data["requester_id"] = self.current_user.id

        schema = FollowupRequest.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": followup_request.obj_id},
        )
        return self.success()

    @auth_or_token
    def delete(self, request_id):
        """
        ---
        description: Delete follow-up request.
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        followup_request = FollowupRequest.query.get(int(request_id))
        if hasattr(self.current_user, "roles"):
            if not (
                "Super admin" in [role.id for role in self.current_user.roles]
                or "Group admin" in [role.id for role in self.current_user.roles]
                or followup_request.requester.username == self.current_user.username
            ):
                return self.error("Insufficient permissions.")
        elif isinstance(self.current_user, Token):
            if self.current_user.created_by_id != followup_request.requester.id:
                return self.error("Insufficient permissions.")
        DBSession().delete(followup_request)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": followup_request.obj_id},
        )
        return self.success()
