import jsonschema
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    EventObservationPlan,
    ObservationPlanRequest,
    Group,
    Allocation,
)

from ...models.schema import ObservationPlanPost


class ObservationPlanRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Submit observation plan request.
        tags:
          - observationplan_requests
        requestBody:
          content:
            application/json:
              schema: ObservationPlanPost
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
                              description: New observation plan request ID
        """
        data = self.get_json()

        try:
            data = ObservationPlanPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])
        data['localization_id'] = int(data['localization_id'])

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'],
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument
        if instrument.api_classname_obsplan is None:
            return self.error('Instrument has no remote API.')

        if not instrument.api_class_obsplan.implements()['submit']:
            return self.error(
                'Cannot submit observation plan requests for this Instrument.'
            )

        target_groups = []
        for group_id in data.pop('target_group_ids', []):
            g = Group.get_if_accessible_by(
                group_id, self.current_user, raise_if_none=True
            )
            target_groups.append(g)

        # validate the payload
        jsonschema.validate(
            data['payload'], instrument.api_class_obsplan.form_json_schema
        )

        observationplan_request = ObservationPlanRequest.__schema__().load(data)
        observationplan_request.target_groups = target_groups
        DBSession().add(observationplan_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observationplan_request.gcnevent.dateobs},
        )

        try:
            instrument.api_class_obsplan.submit(observationplan_request)
        except Exception as e:
            observationplan_request.status = 'failed to submit'
            return self.error(f'Error submitting observation plan: {e.args[0]}')
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observationplan_request.gcnevent.dateobs},
        )

        return self.success(data={"id": observationplan_request.id})

    @auth_or_token
    def get(self, observation_plan_request_id):
        """
        ---
        description: Get an observation plan.
        tags:
          - observationplan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
          - in: query
            name: includePlannedObservations
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include associated planned observations. Defaults to false.
        responses:
          200:
            content:
              application/json:
                schema: SingleObservationPlanRequest
        """

        include_planned_observations = self.get_query_argument(
            "includePlannedObservations", False
        )
        if include_planned_observations:
            options = [
                joinedload(ObservationPlanRequest.observation_plans).joinedload(
                    EventObservationPlan.planned_observations
                )
            ]
        else:
            options = [joinedload(ObservationPlanRequest.observation_plans)]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        return self.success(data=observation_plan_request)

    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Delete observation plan.
        tags:
          - observationplan_requests
        parameters:
          - in: path
            name: observation_plan_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="delete",
            raise_if_none=True,
        )
        dateobs = observation_plan_request.gcnevent.dateobs

        api = observation_plan_request.instrument.api_class_obsplan
        if not api.implements()['delete']:
            return self.error('Cannot delete observation plans on this instrument.')

        observation_plan_request.last_modified_by_id = self.associated_user_object.id
        api.delete(observation_plan_request.id)

        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": dateobs},
        )

        return self.success()
