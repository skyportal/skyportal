import jsonschema
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Source,
    FollowupRequest,
    ClassicalAssignment,
    ObservingRun,
    Obj,
    Group,
    Allocation,
)

from sqlalchemy.orm import joinedload

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

        # get owned assignments
        assignments = DBSession().query(ClassicalAssignment)
        assignments = (
            assignments.join(Obj)
            .join(Source)
            .join(Group)
            .filter(Group.id.in_([g.id for g in self.current_user.accessible_groups]))
        )

        if assignment_id is not None:
            try:
                assignment_id = int(assignment_id)
            except ValueError:
                return self.error("Assignment ID must be an integer.")

            assignments = assignments.filter(
                ClassicalAssignment.id == assignment_id
            ).options(
                joinedload(ClassicalAssignment.obj).joinedload(Obj.thumbnails),
                joinedload(ClassicalAssignment.requester),
                joinedload(ClassicalAssignment.obj),
            )

        assignments = assignments.all()

        if len(assignments) == 0 and assignment_id is not None:
            return self.error("Could not retrieve assignment.")

        out_json = ClassicalAssignment.__schema__().dump(assignments, many=True)

        # calculate when the targets rise and set
        for json_obj, assignment in zip(out_json, assignments):
            json_obj['rise_time_utc'] = assignment.rise_time.isot
            json_obj['set_time_utc'] = assignment.set_time.isot
            json_obj['obj'] = assignment.obj
            json_obj['requester'] = assignment.requester

        if assignment_id is not None:
            out_json = out_json[0]

        return self.success(data=out_json)

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
            return self.error(
                'Error parsing followup request: ' f'"{e.normalized_messages()}"'
            )

        run_id = assignment.run_id
        data['priority'] = assignment.priority.name
        run = ObservingRun.query.get(run_id)
        if run is None:
            return self.error(f'Invalid observing run: "{run_id}"')

        predecessor = ClassicalAssignment.query.filter(
            ClassicalAssignment.obj_id == assignment.obj_id,
            ClassicalAssignment.run_id == run_id,
        ).first()

        if predecessor is not None:
            return self.error('Object is already assigned to this run.')

        assignment = ClassicalAssignment(**data)
        source = Source.get_obj_if_owned_by(assignment.obj_id, self.current_user)

        if source is None:
            return self.error(f'Invalid obj_id: "{assignment.obj_id}"')

        assignment.requester_id = self.associated_user_object.id
        DBSession().add(assignment)
        DBSession().commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": assignment.obj.internal_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success(data={"id": assignment.id})

    @auth_or_token
    def put(self, assignment_id):
        """
        ---
        description: Update an assignment
        parameters:
          - in: path
            name: assignment_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: ClassicalAssignmentNoID
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
        assignment = ClassicalAssignment.query.get(int(assignment_id))

        if assignment is None:
            return self.error('No such assignment')

        data = self.get_json()
        data['id'] = assignment_id
        data["requester_id"] = self.associated_user_object.id

        modok = (
            "System admin" in self.current_user.permissions
            or assignment.requester.username == self.current_user.username
        )
        if not modok:
            return self.error("Insufficient permissions.")

        schema = ClassicalAssignment.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": assignment.obj.internal_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success()

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
        delok = (
            "System admin" in [a.id for a in user.acls]
            or assignment.requester.username == user.username
        )
        if not delok:
            return self.error("Insufficient permissions.")

        obj_key = assignment.obj.internal_key

        DBSession().delete(assignment)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success()


class FollowupRequestHandler(BaseHandler):
    @auth_or_token
    def get(self, followup_request_id=None):
        """
        ---
        single:
          description: Retrieve a followup request
          parameters:
            - in: path
              name: followup_request_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleFollowupRequest
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all followup requests
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfFollowupRequests
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned assignments
        followup_requests = DBSession().query(FollowupRequest)
        followup_requests = (
            followup_requests.join(Obj)
            .join(Source)
            .join(Group)
            .filter(Group.id.in_([g.id for g in self.current_user.accessible_groups]))
        )

        if followup_request_id is not None:
            try:
                followup_request_id = int(followup_request_id)
            except ValueError:
                return self.error("Assignment ID must be an integer.")

            followup_requests = followup_requests.filter(
                FollowupRequest.id == followup_request_id
            ).options(
                joinedload(FollowupRequest.obj).joinedload(Obj.thumbnails),
                joinedload(FollowupRequest.requester),
                joinedload(FollowupRequest.obj),
            )
            followup_request = followup_requests.first()
            if followup_request is None:
                return self.error("Could not retrieve followup request.")
            return self.success(data=followup_request)

        followup_requests = followup_requests.all()

        return self.success(data=followup_requests)

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
        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])

        allocation = Allocation.query.get(data['allocation_id'])
        if allocation is None:
            return self.error('No such allocation.')
        if allocation.group_id not in [
            g.id for g in self.current_user.accessible_groups
        ]:
            return self.error('User does not have access to this allocation.')

        instrument = allocation.instrument
        if instrument.api_classname is None:
            return self.error('Instrument has no remote API.')

        if not instrument.api_class.implements()['submit']:
            return self.error('Cannot submit followup requests to this Instrument.')

        # validate the payload
        jsonschema.validate(data['payload'], instrument.api_class.form_json_schema)

        followup_request = FollowupRequest.__schema__().load(data)
        DBSession().add(followup_request)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )

        try:
            instrument.api_class.submit(followup_request)
        except Exception:
            followup_request.status = 'failed to submit'
            raise
        finally:
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

        followup_request = FollowupRequest.get_if_owned_by(
            request_id, self.current_user
        )

        data = self.get_json()
        data['id'] = request_id
        data["last_modified_by_id"] = self.associated_user_object.id

        api = followup_request.instrument.api_class

        if not api.implements()['update']:
            return self.error('Cannot update requests on this instrument.')

        # validate posted data
        try:
            FollowupRequest.__schema__().load(data, partial=True)
        except ValidationError as e:
            return self.error(
                f'Error parsing followup request update: "{e.normalized_messages()}"'
            )

        for k in data:
            setattr(followup_request, k, data[k])

        followup_request.instrument.api_class.update(followup_request)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
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
        followup_request = FollowupRequest.get_if_owned_by(
            request_id, self.current_user
        )
        if not (
            "Super admin" in [role.id for role in self.associated_user_object.roles]
            or "Group admin" in [role.id for role in self.associated_user_object.roles]
            or followup_request.requester.username
            == self.associated_user_object.username
        ):
            return self.error("Insufficient permissions.")

        api = followup_request.instrument.api_class
        if not api.implements()['delete']:
            return self.error('Cannot delete requests on this instrument.')

        followup_request.last_modified_by_id = self.associated_user_object.id
        api.delete(followup_request)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )
        return self.success()
