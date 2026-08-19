/**
 * Default analyses (per analysis service).
 *
 * A DefaultAnalysis auto-runs an analysis service when a source matches its
 * source_filter — either a classification (name + probability) or a group
 * (saved-to-group trigger). Nested under the analysis service.
 */
import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

export const defaultAnalysesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultAnalyses: build.query<
      RouteData<"GET /api/analysis_service/{analysis_service_id}/default_analysis">,
      number | string
    >({
      query: (analysisServiceId) =>
        `api/analysis_service/${analysisServiceId}/default_analysis`,
      providesTags: ["DefaultAnalysis"],
    }),
    submitDefaultAnalysis: build.mutation<
      any,
      { analysisServiceId: number | string; body: any }
    >({
      query: ({ analysisServiceId, body }) => ({
        url: `api/analysis_service/${analysisServiceId}/default_analysis`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["DefaultAnalysis"],
    }),
    deleteDefaultAnalysis: build.mutation<
      unknown,
      { analysisServiceId: number | string; defaultAnalysisId: number | string }
    >({
      query: ({ analysisServiceId, defaultAnalysisId }) => ({
        url: `api/analysis_service/${analysisServiceId}/default_analysis/${defaultAnalysisId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["DefaultAnalysis"],
    }),
  }),
});

export const {
  useGetDefaultAnalysesQuery,
  useSubmitDefaultAnalysisMutation,
  useDeleteDefaultAnalysisMutation,
} = defaultAnalysesApi;
