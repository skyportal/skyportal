from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token

from ...models import (
    DefaultObservationPlanRequest,
    DefaultSurveyEfficiencyRequest,
    SurveyEfficiencyForObservationPlan,
    SurveyEfficiencyForObservations,
)
from ..base import BaseHandler


class SurveyEfficiencyForObservationPlanHandler(BaseHandler):
    @auth_or_token
    def get(self, survey_efficiency_analysis_id=None):
        """
        ---
        single:
          tags:
            - survey efficiency
          summary: Retrieve an observation plan efficiency analysis
          description: Retrieve an observation plan efficiency analysis
          parameters:
            - in: path
              name: survey_efficiency_analysis_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleSurveyEfficiencyForObservationPlan
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - allocations
          summary: Retrieve all observation plan efficiency analyses
          description: Retrieve all observation plan efficiency analyses
          parameters:
          - in: query
            name: observation_plan_id
            nullable: true
            schema:
              type: number
            description: EventObservationPlan ID to retrieve observation plan efficiency analyses for
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfSurveyEfficiencyForObservationPlans
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned efficiency analyses
        survey_efficiency_analyses = (
            SurveyEfficiencyForObservationPlan.query_records_accessible_by(
                self.current_user
            )
        )

        if survey_efficiency_analysis_id is not None:
            try:
                survey_efficiency_analysis_id = int(survey_efficiency_analysis_id)
            except ValueError:
                return self.error(
                    "SurveyEfficiencyForObservationPlan ID must be an integer."
                )
            survey_efficiency_analyses = survey_efficiency_analyses.filter(
                SurveyEfficiencyForObservationPlan.id == survey_efficiency_analysis_id
            ).all()
            if len(survey_efficiency_analyses) == 0:
                return self.error("Could not retrieve survey efficiency analyses.")
            return self.success(data=survey_efficiency_analyses[0])

        observation_plan_id = self.get_query_argument("observation_plan_id", None)
        if observation_plan_id is not None:
            survey_efficiency_analyses = survey_efficiency_analyses.filter(
                SurveyEfficiencyForObservationPlan.observation_plan_id
                == observation_plan_id
            )

        survey_efficiency_analyses = survey_efficiency_analyses.all()
        self.verify_and_commit()

        return self.success(data=survey_efficiency_analyses)


class SurveyEfficiencyForObservationsHandler(BaseHandler):
    @auth_or_token
    def get(self, survey_efficiency_analysis_id=None):
        """
        ---
        single:
          tags:
            - survey efficiency
          summary: Retrieve an observation efficiency analysis
          description: Retrieve an observation efficiency analysis
          parameters:
            - in: path
              name: survey_efficiency_analysis_id
              required: true
              schema:
                type: integer
          responses:
            200:
               content:
                application/json:
                  schema: SingleSurveyEfficiencyForObservations
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - allocations
          summary: Retrieve all observation efficiencies
          description: Retrieve all observation analyses
          parameters:
          - in: query
            name: gcnevent_id
            nullable: true
            schema:
              type: number
            description: GcnEvent  ID to retrieve observation efficiency analyses for
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfSurveyEfficiencyForObservationss
            400:
              content:
                application/json:
                  schema: Error
        """

        # get owned efficiency analyses
        survey_efficiency_analyses = (
            SurveyEfficiencyForObservations.query_records_accessible_by(
                self.current_user
            )
        )

        if survey_efficiency_analysis_id is not None:
            try:
                survey_efficiency_analysis_id = int(survey_efficiency_analysis_id)
            except ValueError:
                return self.error(
                    "SurveyEfficiencyForObservations ID must be an integer."
                )
            survey_efficiency_analyses = survey_efficiency_analyses.filter(
                SurveyEfficiencyForObservationPlan.id == survey_efficiency_analysis_id
            ).all()
            if len(survey_efficiency_analyses) == 0:
                return self.error("Could not retrieve survey efficiency analyses.")
            return self.success(data=survey_efficiency_analyses[0])

        gcnevent_id = self.get_query_argument("gcnevent_id", None)
        if gcnevent_id is not None:
            survey_efficiency_analyses = survey_efficiency_analyses.filter(
                SurveyEfficiencyForObservations.gcnevent_id == gcnevent_id
            )

        survey_efficiency_analyses = survey_efficiency_analyses.all()
        self.verify_and_commit()

        return self.success(data=survey_efficiency_analyses)


class DefaultSurveyEfficiencyRequestHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Create default survey efficiency requests
        description: Create default survey efficiency requests.
        tags:
          - default survey efficiency
        requestBody:
          content:
            application/json:
              schema: DefaultSurveyEfficiencyPost
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
                              description: New default survey efficiency request ID
        """
        data = self.get_json()

        with self.Session() as session:
            stmt = DefaultObservationPlanRequest.select(session.user_or_token).where(
                DefaultObservationPlanRequest.id
                == data["default_observationplan_request_id"],
            )
            default_observation_plan = session.scalars(stmt).first()
            if default_observation_plan is None:
                return self.error(
                    f"Missing allocation with ID: {data['default_observation_plan_id']}",
                    status=403,
                )

            default_survey_efficiency_request = (
                DefaultSurveyEfficiencyRequest.__schema__().load(data)
            )
            session.add(default_survey_efficiency_request)
            session.commit()

            self.push_all(action="skyportal/REFRESH_DEFAULT_SURVEY_EFFICIENCIES")
            return self.success(data={"id": default_survey_efficiency_request.id})

    @auth_or_token
    def get(self, default_survey_efficiency_id=None):
        """
        ---
        single:
          summary: Retrieve a default survey efficiency
          description: Retrieve a single default survey efficiency
          tags:
            - default survey efficiency
          parameters:
            - in: path
              name: default_survey_efficiency_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleDefaultSurveyEfficiencyRequest
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve all default survey efficiencies
          description: Retrieve all default survey efficiencies
          tags:
            - default survey efficiency
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfDefaultSurveyEfficiencyRequests
            400:
              content:
                application/json:
                  schema: Error
        """

        with self.Session() as session:
            if default_survey_efficiency_id is not None:
                default_survey_efficiency_request = session.scalars(
                    DefaultSurveyEfficiencyRequest.select(
                        session.user_or_token,
                        options=[
                            joinedload(
                                DefaultSurveyEfficiencyRequest.default_observationplan_request
                            )
                        ],
                    ).where(
                        DefaultSurveyEfficiencyRequest.id
                        == default_survey_efficiency_id
                    )
                ).first()
                if default_survey_efficiency_request is None:
                    return self.error(
                        f"Cannot access default_survey_efficiency_request for id {default_survey_efficiency_id}"
                    )

                return self.success(data=default_survey_efficiency_request)

            default_survey_efficiency_requests = (
                session.scalars(
                    DefaultSurveyEfficiencyRequest.select(
                        session.user_or_token,
                        options=[
                            joinedload(
                                DefaultSurveyEfficiencyRequest.default_observationplan_request
                            )
                        ],
                    )
                )
                .unique()
                .all()
            )

            default_survey_efficiency_data = []
            for request in default_survey_efficiency_requests:
                default_survey_efficiency_data.append(
                    {
                        **request.to_dict(),
                        "default_observationplan_request": request.default_observationplan_request.to_dict(),
                    }
                )

            return self.success(data=default_survey_efficiency_data)

    @auth_or_token
    def delete(self, default_survey_efficiency_id):
        """
        ---
        summary: Delete a default survey efficiency
        description: Delete a default survey efficiency
        tags:
          - default survey efficiency
        parameters:
          - in: path
            name: default_survey_efficiency_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        with self.Session() as session:
            stmt = DefaultSurveyEfficiencyRequest.select(session.user_or_token).where(
                DefaultSurveyEfficiencyRequest.id == default_survey_efficiency_id
            )
            default_survey_efficiency_request = session.scalars(stmt).first()

            if default_survey_efficiency_request is None:
                return self.error(
                    "Default survey efficiency with ID {default_survey_efficiency_id} is not available."
                )

            session.delete(default_survey_efficiency_request)
            session.commit()
            self.push_all(action="skyportal/REFRESH_DEFAULT_SURVEY_EFFICIENCIES")
            return self.success()
