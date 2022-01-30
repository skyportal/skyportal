import jsonschema
from marshmallow.exceptions import ValidationError

from baselayer.app.access import permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    ObservationPlanRequest,
    Group,
    Allocation,
)

from ...models.schema import ObservationPlanPost


class ObservationPlanRequestHandler(BaseHandler):
    @permissions(["Upload data"])
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
        if instrument.api_observationplan_classname is None:
            return self.error('Instrument has no remote API.')

        if not instrument.api_observationplan_class.implements()['submit']:
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
            data['payload'], instrument.api_observationplan_class.form_json_schema
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
            instrument.api_observationplan_class.submit(observationplan_request)
        except Exception:
            observationplan_request.status = 'failed to submit'
            raise
        finally:
            self.verify_and_commit()
            self.push_all(
                action="skyportal/REFRESH_GCNEVENT",
                payload={"gcnEvent_dateobs": observationplan_request.gcnevent.dateobs},
            )

        return self.success(data={"id": observationplan_request.id})

    @permissions(["Upload data"])
    def delete(self, observation_plan_id):
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
        observationplan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_id, self.current_user, mode="delete", raise_if_none=True
        )

        dateobs = observationplan_request.gcnevent.dateobs
        DBSession.delete(observationplan_request)

        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": dateobs},
        )

        return self.success()
