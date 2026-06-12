/**
 * Default survey efficiencies.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_SURVEY_EFFICIENCIES` duck.
 * Websocket-driven invalidation refetches the list; mutations submit/delete a
 * default survey efficiency.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export const defaultSurveyEfficienciesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultSurveyEfficiencies: build.query<
      RouteData<"GET /api/default_survey_efficiency">,
      Record<string, unknown> | void
    >({
      query: (filterParams) => {
        const params = new URLSearchParams(
          (filterParams as Record<string, string>) ?? {},
        ).toString();
        return params
          ? `api/default_survey_efficiency?${params}`
          : "api/default_survey_efficiency";
      },
      providesTags: ["DefaultSurveyEfficiency"],
    }),
    submitDefaultSurveyEfficiency: build.mutation<unknown, Record<string, any>>(
      {
        query: (data) => ({
          url: "api/default_survey_efficiency",
          method: "POST",
          body: data,
        }),
        invalidatesTags: ["DefaultSurveyEfficiency"],
      },
    ),
    deleteDefaultSurveyEfficiency: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/default_survey_efficiency/${id}`,
        method: "DELETE",
      }),
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
