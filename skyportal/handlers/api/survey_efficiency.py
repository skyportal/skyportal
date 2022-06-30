from baselayer.app.access import auth_or_token

from ..base import BaseHandler
from ...models import (
    SurveyEfficiencyForObservations,
    SurveyEfficiencyForObservationPlan,
)


class SurveyEfficiencyForObservationPlanHandler(BaseHandler):
    @auth_or_token
    def get(self, survey_efficiency_analysis_id=None):
        """
        ---
        single:
          tags:
            - survey_efficiency_for_observation_plans
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

        observation_plan_id = self.get_query_argument('observation_plan_id', None)
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
            - survey_efficiency_for_observations
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

        gcnevent_id = self.get_query_argument('gcnevent_id', None)
        if gcnevent_id is not None:
            survey_efficiency_analyses = survey_efficiency_analyses.filter(
                SurveyEfficiencyForObservations.gcnevent_id == gcnevent_id
            )

        survey_efficiency_analyses = survey_efficiency_analyses.all()
        self.verify_and_commit()

        return self.success(data=survey_efficiency_analyses)
