import astropy
import jsonschema
from marshmallow.exceptions import ValidationError
import numpy as np
import healpix_alchemy as ha
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    Allocation,
    DBSession,
    EventObservationPlan,
    GcnEvent,
    Group,
    InstrumentFieldTile,
    ObservationPlanRequest,
    PlannedObservation,
    LocalizationTile,
)

from ...models.schema import ObservationPlanPost


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
    def get(self, observation_plan_request_id=None):
        """
        ---
        single:
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
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Get all observation plans.
          tags:
            - observation_plan_requests
          parameters:
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
                  schema: ArrayOfObservationPlanRequests
            400:
              content:
                application/json:
                  schema: Error
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

        if observation_plan_request_id is not None:
            observation_plan_request = ObservationPlanRequest.get_if_accessible_by(
                observation_plan_request_id,
                self.current_user,
                mode="read",
                raise_if_none=True,
                options=options,
            )
            return self.success(data=observation_plan_request)

        query = ObservationPlanRequest.query_records_accessible_by(
            self.current_user, mode="read", options=options
        )
        observation_plan_requests = query.all()
        self.verify_and_commit()
        return self.success(data=observation_plan_requests)

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


class ObservationPlanGCNHandler(BaseHandler):
    @auth_or_token
    def get(self, observation_plan_request_id):
        """
        ---
        description: Get a GCN-izable summary of the observation plan.
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

        filters, dates = [], []
        for obs in observation_plan_request.observation_plans[0].planned_observations:
            filters.append(obs.filt)
            dates.append(astropy.time.Time(obs.obstime, format='datetime'))

        filtersUnique = list(set(filters))
        minDate = min(dates)
        trigger_time = astropy.time.Time(event.dateobs, format='datetime')
        dt = minDate - trigger_time

        union = (
            sa.select(ha.func.union(InstrumentFieldTile.healpix).label('healpix'))
            .filter(
                InstrumentFieldTile.instrument_field_id == PlannedObservation.field_id,
                PlannedObservation.observation_plan_id
                == observation_plan_request.observation_plans[0].id,
            )
            .subquery()
        )

        area = sa.func.sum(union.columns.healpix.area)
        prob = sa.func.sum(
            LocalizationTile.probdensity
            * (union.columns.healpix * LocalizationTile.healpix).area
        )
        query_area = sa.select(area).filter(
            LocalizationTile.localization_id
            == observation_plan_request.localization_id,
            union.columns.healpix.overlaps(LocalizationTile.healpix),
        )
        query_prob = sa.select(prob).filter(
            LocalizationTile.localization_id
            == observation_plan_request.localization_id,
            union.columns.healpix.overlaps(LocalizationTile.healpix),
        )
        intprob = DBSession().execute(query_prob).scalar_one()
        intarea = DBSession().execute(query_area).scalar_one()

        content = [
            "SUBJECT: Follow-up of ",
            event.gcn_notices[0].stream,
            " trigger",
            trigger_time.isot,
            " with ",
            instrument.name,
            "\nWe observed the localization region of ",
            event.gcn_notices[0].stream,
            " trigger ",
            trigger_time.isot,
            " UTC with ",
            instrument.name,
            " on the ",
            instrument.telescope.name,
            ". We obtained a series of ",
            ",".join(filtersUnique),
            " band images covering ",
            "%.2f" % (intarea * (180.0 / np.pi) ** 2),
            " square degrees beginning at ",
            minDate.isot,
            " (",
            "%.2f" % dt.jd,
            " days after the burst trigger time) corresponding to ~",
            "%.2f" % (100 * intprob),
            "% of the probability enclosed in the localization region.\n\n",
        ]

        return self.success(data="".join(content))
