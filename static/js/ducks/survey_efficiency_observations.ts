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
import type { FetchObservationSimSurveyOptions } from "skyportal-js/Observations";
import type { SurveyEfficiencyForObservations } from "skyportal-js/SurveyEfficiency";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const surveyEfficiencyObservationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSurveyEfficiencyObservations: build.query<
      SurveyEfficiencyForObservations[],
      void
    >({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) =>
          client.fetchSurveyEfficienciesForObservations(),
        ),
      providesTags: ["SurveyEfficiencyObservation"],
    }),
    // A GET that starts the analysis, so it stays a mutation here.
    submitSurveyEfficiencyObservations: build.mutation<
      unknown,
      {
        id: number | string;
        data: {
          startDate: string;
          endDate: string;
          localizationDateobs: string;
        } & FetchObservationSimSurveyOptions;
      }
    >({
      queryFn: ({ id, data }, api) => {
        const { startDate, endDate, localizationDateobs, ...options } = data;
        return clientQuery(api, (client) =>
          client.fetchObservationSimSurvey(
            Number(id),
            startDate,
            endDate,
            localizationDateobs,
            options,
          ),
        );
      },
      invalidatesTags: ["SurveyEfficiencyObservation"],
    }),
    deleteSurveyEfficiencyObservations: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.deleteObservationSimSurvey(Number(id)),
        ),
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
