/**
 * Default survey efficiencies.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_SURVEY_EFFICIENCIES` duck.
 * Websocket-driven invalidation refetches the list; mutations submit/delete a
 * default survey efficiency.
 */
import type { DefaultSurveyEfficiencyRequest } from "skyportal-js/SurveyEfficiency";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const defaultSurveyEfficienciesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed filter params
    // that the server ignored.
    getDefaultSurveyEfficiencies: build.query<
      DefaultSurveyEfficiencyRequest[],
      void
    >({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchDefaultSurveyEfficiencies()),
      providesTags: ["DefaultSurveyEfficiency"],
    }),
    submitDefaultSurveyEfficiency: build.mutation<
      { id: number },
      {
        default_observationplan_request_id: number | string;
        payload?: Record<string, unknown>;
      }
    >({
      queryFn: ({ default_observationplan_request_id, payload }, api) =>
        clientQuery(api, (client) =>
          client.postDefaultSurveyEfficiency(
            Number(default_observationplan_request_id),
            { payload },
          ),
        ),
      invalidatesTags: ["DefaultSurveyEfficiency"],
    }),
    deleteDefaultSurveyEfficiency: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.deleteDefaultSurveyEfficiency(Number(id)),
        ),
      invalidatesTags: ["DefaultSurveyEfficiency"],
    }),
  }),
});

// Websocket: the old handler refetched the full list on
// REFRESH_DEFAULT_SURVEY_EFFICIENCIES.
invalidateOnMessage("skyportal/REFRESH_DEFAULT_SURVEY_EFFICIENCIES", () => [
  "DefaultSurveyEfficiency",
]);

export const {
  useGetDefaultSurveyEfficienciesQuery,
  useSubmitDefaultSurveyEfficiencyMutation,
  useDeleteDefaultSurveyEfficiencyMutation,
} = defaultSurveyEfficienciesApi;
