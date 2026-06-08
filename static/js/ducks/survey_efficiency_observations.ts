/**
 * Survey efficiency analyses for observations.
 *
 * RTK Query conversion of the old `FETCH_SURVEY_EFFICIENCY_OBSERVATIONS` duck.
 * The endpoint is injected into the central `skyportalApi`. The list query
 * provides the `SurveyEfficiencyObservation` tag; submit and delete are
 * mutations that invalidate it so the active list refetches.
 *
 * Submit issues an `simsurvey` run (the backend kicks off the analysis); the
 * old duck used `API.GET` for it, so the mutation keeps the `GET` method with
 * the form data as query params. The websocket
 * `REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

type SurveyEfficiencyObservation = Record<string, any>;

export const surveyEfficiencyObservationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSurveyEfficiencyObservations: build.query<
      SurveyEfficiencyObservation[],
      Record<string, any> | void
    >({
      query: (params) => ({
        url: "api/survey_efficiency/observations",
        params: params ?? {},
      }),
      providesTags: ["SurveyEfficiencyObservation"],
    }),
    submitSurveyEfficiencyObservations: build.mutation<
      unknown,
      { id: number | string; data?: Record<string, any> | undefined }
    >({
      query: ({ id, data = {} }) => ({
        url: `api/observation/simsurvey/${id}`,
        method: "GET",
        params: data,
      }),
      invalidatesTags: ["SurveyEfficiencyObservation"],
    }),
    deleteSurveyEfficiencyObservations: build.mutation<
      unknown,
      number | string
    >({
      query: (id) => ({
        url: `api/observation/simsurvey/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["SurveyEfficiencyObservation"],
    }),
  }),
});

// Websocket: old handler refetched on REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS.
invalidateOnMessage("skyportal/REFRESH_SURVEY_EFFICIENCY_OBSERVATIONS", () => [
  "SurveyEfficiencyObservation",
]);

export const {
  useGetSurveyEfficiencyObservationsQuery,
  useSubmitSurveyEfficiencyObservationsMutation,
  useDeleteSurveyEfficiencyObservationsMutation,
} = surveyEfficiencyObservationsApi;
