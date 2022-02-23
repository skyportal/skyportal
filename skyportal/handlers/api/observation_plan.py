import jsonschema
import requests
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload
import urllib
from astropy.time import Time

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    EventObservationPlan,
    GcnEvent,
    Group,
    Allocation,
    ObservationPlanRequest,
    PlannedObservation,
)

from ...models.schema import ObservationPlanPost

env, cfg = load_env()
TREASUREMAP_URL = cfg['app.treasuremap_endpoint']


class ObservationPlanRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Submit observation plan request.
        tags:
          - observation_plan_requests
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

        observation_plan_request = ObservationPlanRequest.__schema__().load(data)
        observation_plan_request.target_groups = target_groups
        DBSession().add(observation_plan_request)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        try:
            instrument.api_class_obsplan.submit(observation_plan_request)
        except Exception as e:
            observation_plan_request.status = 'failed to submit'
            return self.error(f'Error submitting observation plan: {e.args[0]}')
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        return self.success(data={"id": observation_plan_request.id})

    @auth_or_token
    def get(self, observation_plan_request_id):
        """
        ---
        description: Get an observation plan.
        tags:
          - observation_plan_requests
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
          - observation_plan_requests
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


class ObservationPlanSubmitHandler(BaseHandler):
    @auth_or_token
    def post(self, observation_plan_request_id):
        """
        ---
        description: Submit an observation plan.
        tags:
          - observation_plan_requests
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
                schema: SingleObservationPlanRequest
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )

        api = observation_plan_request.instrument.api_class_obsplan
        if not api.implements()['send']:
            return self.error('Cannot send observation plans on this instrument.')

        try:
            api.send(observation_plan_request)
        except Exception as e:
            observation_plan_request.status = 'failed to send'
            return self.error(
                f'Error sending observation plan to telescope: {e.args[0]}'
            )
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        self.verify_and_commit()

        return self.success(data=observation_plan_request)

    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Remove an observation plan from the queue.
        tags:
          - observation_plan_requests
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
            mode="read",
            raise_if_none=True,
        )

        api = observation_plan_request.instrument.api_class_obsplan
        if not api.implements()['remove']:
            return self.error(
                'Cannot remove observation plans from the queue of this instrument.'
            )

        try:
            api.remove(observation_plan_request)
        except Exception as e:
            observation_plan_request.status = 'failed to remove from queue'
            return self.error(
                f'Error removing observation plan from telescope: {e.args[0]}'
            )
        finally:
            self.verify_and_commit()
        self.push_all(
            action="skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": observation_plan_request.gcnevent.dateobs},
        )

        self.verify_and_commit()

        return self.success(data=observation_plan_request)


class ObservationPlanTreasureMapHandler(BaseHandler):
    @auth_or_token
    def post(self, observation_plan_request_id):
        """
        ---
        description: Submit the observation plan to treasuremap.space
        tags:
          - observation_plan_requests
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
          400:
            content:
              application/json:
                schema: Error
        """

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(GcnEvent.gcn_notices),
                ],
            )
            .filter(GcnEvent.id == observation_plan_request.gcnevent_id)
            .first()
        )

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument

        altdata = allocation.altdata
        if not altdata:
            raise self.error('Missing allocation information.')

        observation_plan = observation_plan_request.observation_plans[0]
        planned_observations = observation_plan.planned_observations

        if len(planned_observations) == 0:
            return self.error('Cannot submit observing plan with no observations.')

        graceid = event.graceid
        payload = {"graceid": graceid, "api_token": altdata['TREASUREMAP_API_TOKEN']}

        pointings = []
        for obs in planned_observations:
            pointing = {}
            pointing["ra"] = obs.field.ra
            pointing["dec"] = obs.field.dec
            pointing["band"] = obs.filt
            pointing["instrumentid"] = str(instrument.treasuremap_id)
            pointing["status"] = "planned"
            pointing["time"] = Time(obs.obstime, format='datetime').isot
            pointing["depth"] = 0.0
            pointing["depth_unit"] = "ab_mag"
            pointings.append(pointing)

        payload["pointings"] = pointings

        url = urllib.parse.urljoin(TREASUREMAP_URL, 'api/v0/pointings')
        r = requests.post(url=url, json=payload)
        r.raise_for_status()

        return self.success()

    @auth_or_token
    def delete(self, observation_plan_request_id):
        """
        ---
        description: Remove observation plan from treasuremap.space.
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

        options = [
            joinedload(ObservationPlanRequest.observation_plans)
            .joinedload(EventObservationPlan.planned_observations)
            .joinedload(PlannedObservation.field)
        ]

        observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
            observation_plan_request_id,
            self.current_user,
            mode="read",
            raise_if_none=True,
            options=options,
        )
        self.verify_and_commit()

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(GcnEvent.gcn_notices),
                ],
            )
            .filter(GcnEvent.id == observation_plan_request.gcnevent_id)
            .first()
        )

        allocation = Allocation.get_if_accessible_by(
            observation_plan_request.allocation_id,
            self.current_user,
            raise_if_none=True,
        )

        instrument = allocation.instrument

        altdata = allocation.altdata
        if not altdata:
            raise self.error('Missing allocation information.')

        graceid = event.graceid
        payload = {
            "graceid": graceid,
            "api_token": altdata['TREASUREMAP_API_TOKEN'],
            "instrumentid": instrument.treasuremap_id,
        }

        baseurl = urllib.parse.urljoin(TREASUREMAP_URL, 'api/v0/cancel_all')
        url = f"{baseurl}?{urllib.parse.urlencode(payload)}"
        r = requests.post(url=url)
        r.raise_for_status()

        return self.success()
