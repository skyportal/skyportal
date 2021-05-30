import jsonschema
from marshmallow.exceptions import ValidationError


from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    FollowupRequest,
    ClassicalAssignment,
    ObservingRun,
    Obj,
    Group,
    Allocation,
)

from sqlalchemy.orm import joinedload

from ...schema import AssignmentSchema, FollowupRequestPost


class AssignmentHandler(BaseHandler):
    @auth_or_token
    def get(self, assignment_id=None):
        """
        ---
        single:
          description: Retrieve an observing run assignment
          tags:
            - assignments
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
          tags:
            - assignments
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
        assignments = ClassicalAssignment.query_records_accessible_by(self.current_user)

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

        self.verify_and_commit()
        return self.success(data=out_json)

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Post new target assignment to observing run
        tags:
          - assignments
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
        ObservingRun.get_if_accessible_by(run_id, self.current_user, raise_if_none=True)

        predecessor = (
            ClassicalAssignment.query_records_accessible_by(self.current_user)
            .filter(
                ClassicalAssignment.obj_id == assignment.obj_id,
                ClassicalAssignment.run_id == run_id,
            )
            .first()
        )

        if predecessor is not None:
            return self.error('Object is already assigned to this run.')

        assignment = ClassicalAssignment(**data)

        assignment.requester_id = self.associated_user_object.id
        DBSession().add(assignment)
        self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": assignment.obj.internal_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success(data={"id": assignment.id})

    @permissions(["Upload data"])
    def put(self, assignment_id):
        """
        ---
        description: Update an assignment
        tags:
          - assignments
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
        assignment = ClassicalAssignment.get_if_accessible_by(
            int(assignment_id), self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()
        data['id'] = assignment_id
        data["last_modified_by_id"] = self.associated_user_object.id

        schema = ClassicalAssignment.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": assignment.obj.internal_key},
        )
        self.push_all(
            action="skyportal/REFRESH_OBSERVING_RUN",
            payload={"run_id": assignment.run_id},
        )
        return self.success()

    @permissions(["Upload data"])
    def delete(self, assignment_id):
        """
        ---
        description: Delete assignment.
        tags:
          - assignments
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
        assignment = ClassicalAssignment.get_if_accessible_by(
            int(assignment_id), self.current_user, mode="delete", raise_if_none=True
        )
        obj_key = assignment.obj.internal_key
        DBSession().delete(assignment)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": obj_key},
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
          tags:
            - followup_requests
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
          tags:
            - followup_requests
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
        followup_requests = FollowupRequest.query_records_accessible_by(
            self.current_user
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
            self.verify_and_commit()
            return self.success(data=followup_request)

        followup_requests = followup_requests.all()
        self.verify_and_commit()
        return self.success(data=followup_requests)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Submit follow-up request.
        tags:
          - followup_requests
        requestBody:
          content:
            application/json:
              schema: FollowupRequestPost
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

        try:
            data = FollowupRequestPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'], self.current_user, raise_if_none=True
        )
        instrument = allocation.instrument
        if instrument.api_classname is None:
            return self.error('Instrument has no remote API.')

        if not instrument.api_class.implements()['submit']:
            return self.error('Cannot submit followup requests to this Instrument.')

        target_groups = []
        for group_id in data.pop('target_group_ids', []):
            g = Group.get_if_accessible_by(
                group_id, self.current_user, raise_if_none=True
            )
            target_groups.append(g)

        # validate the payload
        jsonschema.validate(data['payload'], instrument.api_class.form_json_schema)

        followup_request = FollowupRequest.__schema__().load(data)
        followup_request.target_groups = target_groups
        DBSession().add(followup_request)
        self.verify_and_commit()

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
            self.verify_and_commit()
            self.push_all(
                action="skyportal/REFRESH_SOURCE",
                payload={"obj_key": followup_request.obj.internal_key},
            )

        return self.success(data={"id": followup_request.id})

    @permissions(["Upload data"])
    def put(self, request_id):
        """
        ---
        description: Update a follow-up request
        tags:
          - followup_requests
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema: FollowupRequestPost
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

        try:
            request_id = int(request_id)
        except ValueError:
            return self.error('Request id must be an int.')

        followup_request = FollowupRequest.get_if_accessible_by(
            request_id, self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()

        try:
            data = FollowupRequestPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data['id'] = request_id
        data["last_modified_by_id"] = self.associated_user_object.id

        api = followup_request.instrument.api_class

        if not api.implements()['update']:
            return self.error('Cannot update requests on this instrument.')

        target_group_ids = data.pop('target_group_ids', None)
        if target_group_ids is not None:
            target_groups = []
            for group_id in target_group_ids:
                g = Group.get_if_accessible_by.get(
                    group_id, self.current_user, raise_if_none=True
                )
                target_groups.append(g)
            followup_request.target_groups = target_groups

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
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )
        return self.success()

    @permissions(["Upload data"])
    def delete(self, request_id):
        """
        ---
        description: Delete follow-up request.
        tags:
          - followup_requests
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
        followup_request = FollowupRequest.get_if_accessible_by(
            request_id, self.current_user, mode="delete", raise_if_none=True
        )

        api = followup_request.instrument.api_class
        if not api.implements()['delete']:
            return self.error('Cannot delete requests on this instrument.')

        followup_request.last_modified_by_id = self.associated_user_object.id
        api.delete(followup_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": followup_request.obj.internal_key},
        )
        return self.success()
