/**
 * Survey efficiency analyses for observation plans.
 *
 * RTK Query conversion of the old `FETCH_SURVEY_EFFICIENCY_OBSERVATION_PLANS`
 * duck. The list query is injected into the central `skyportalApi` and provides
 * the `SurveyEfficiencyObservationPlan` tag; submit and delete are mutations
 * that invalidate it so any active list refetches.
 *
 * Submit issues a `simsurvey` run (the backend kicks off the analysis); the old
 * duck used `API.GET` for it, so the mutation keeps the `GET` method with the
 * form data as query params. The websocket
 * `REFRESH_SURVEY_EFFICIENCY_OBSERVATION_PLANS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export const surveyEfficiencyObservationPlansApi = skyportalApi.injectEndpoints(
  {
    endpoints: (build) => ({
      getSurveyEfficiencyObservationPlans: build.query<
        RouteData<"GET /api/survey_efficiency/observation_plan">,
        void
      >({
        query: () => "api/survey_efficiency/observation_plan",
        providesTags: ["SurveyEfficiencyObservationPlan"],
      }),
      submitSurveyEfficiencyObservationPlan: build.mutation<
        unknown,
        { id: number | string; data?: Record<string, any> | undefined }
      >({
        query: ({ id, data = {} }) => ({
          url: `api/observation_plan/${id}/simsurvey`,
          method: "GET",
          params: data,
        }),
        invalidatesTags: ["SurveyEfficiencyObservationPlan"],
      }),
      deleteSurveyEfficiencyObservationPlan: build.mutation<
        unknown,
        number | string
      >({
        query: (id) => ({
          url: `api/observation_plan/${id}/simsurvey`,
          method: "DELETE",
        }),
        invalidatesTags: ["SurveyEfficiencyObservationPlan"],
      }),
    }),
  },
);

// Websocket: old handler refetched on
// REFRESH_SURVEY_EFFICIENCY_OBSERVATION_PLANS.
invalidateOnMessage(
  "skyportal/REFRESH_SURVEY_EFFICIENCY_OBSERVATION_PLANS",
  () => ["SurveyEfficiencyObservationPlan"],
);

export const {
  useGetSurveyEfficiencyObservationPlansQuery,
  useSubmitSurveyEfficiencyObservationPlanMutation,
  useDeleteSurveyEfficiencyObservationPlanMutation,
} = surveyEfficiencyObservationPlansApi;
