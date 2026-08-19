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
import type { FetchObservationPlanSimSurveyOptions } from "skyportal-js/ObservationPlans";
import type { SurveyEfficiencyForObservationPlan } from "skyportal-js/SurveyEfficiency";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const surveyEfficiencyObservationPlansApi = skyportalApi.injectEndpoints(
  {
    endpoints: (build) => ({
      getSurveyEfficiencyObservationPlans: build.query<
        SurveyEfficiencyForObservationPlan[],
        void
      >({
        queryFn: (_arg, api) =>
          clientQuery(api, (client) =>
            client.fetchSurveyEfficienciesForObservationPlan(),
          ),
        providesTags: ["SurveyEfficiencyObservationPlan"],
      }),
      // A GET that starts the analysis, so it stays a mutation here.
      submitSurveyEfficiencyObservationPlan: build.mutation<
        unknown,
        {
          id: number | string;
          data?: FetchObservationPlanSimSurveyOptions | undefined;
        }
      >({
        queryFn: ({ id, data = {} }, api) =>
          clientQuery(api, (client) =>
            client.fetchObservationPlanSimSurvey(Number(id), data),
          ),
        invalidatesTags: ["SurveyEfficiencyObservationPlan"],
      }),
      deleteSurveyEfficiencyObservationPlan: build.mutation<
        void,
        number | string
      >({
        queryFn: (id, api) =>
          clientQuery(api, (client) =>
            client.deleteObservationPlanSimSurvey(Number(id)),
          ),
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
