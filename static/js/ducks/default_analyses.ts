/**
 * Default analyses (per analysis service).
 *
 * A DefaultAnalysis auto-runs an analysis service when a source matches its
 * source_filter — either a classification (name + probability) or a group
 * (saved-to-group trigger). Nested under the analysis service.
 */
import type {
  DefaultAnalysis,
  DefaultAnalysisPost,
} from "skyportal-js/Analysis";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export const defaultAnalysesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultAnalyses: build.query<DefaultAnalysis[], number | string>({
      queryFn: (analysisServiceId, api) =>
        clientQuery(api, (client) =>
          client.fetchDefaultAnalyses(Number(analysisServiceId)),
        ),
      providesTags: ["DefaultAnalysis"],
    }),
    submitDefaultAnalysis: build.mutation<
      { id: number },
      { analysisServiceId: number | string; body: DefaultAnalysisPost }
    >({
      queryFn: ({ analysisServiceId, body }, api) =>
        clientQuery(api, (client) =>
          client.postDefaultAnalysis(Number(analysisServiceId), body),
        ),
      invalidatesTags: ["DefaultAnalysis"],
    }),
    deleteDefaultAnalysis: build.mutation<
      void,
      { analysisServiceId: number | string; defaultAnalysisId: number | string }
    >({
      queryFn: ({ analysisServiceId, defaultAnalysisId }, api) =>
        clientQuery(api, (client) =>
          client.deleteDefaultAnalysis(
            Number(analysisServiceId),
            Number(defaultAnalysisId),
          ),
        ),
      invalidatesTags: ["DefaultAnalysis"],
    }),
  }),
});

export const {
  useGetDefaultAnalysesQuery,
  useSubmitDefaultAnalysisMutation,
  useDeleteDefaultAnalysisMutation,
} = defaultAnalysesApi;
