/**
 * Analysis services.
 *
 * RTK Query conversion of the old `FETCH_ANALYSIS_SERVICES_LIST` /
 * `FETCH_ANALYSIS_SERVICE` duck. The list query feeds the analysis service
 * pages and dropdowns; mutations submit/modify/delete a service. The websocket
 * `REFRESH_ANALYSIS_SERVICES` message is bridged to cache invalidation via
 * `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface AnalysisService {
  id: number;
  name: string;
  display_name?: string | undefined;
  [key: string]: unknown;
}

interface ModifyAnalysisServiceArg {
  id: number | string;
  params: Record<string, unknown>;
}

export const analysisServicesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAnalysisServices: build.query<
      AnalysisService[],
      Record<string, unknown> | void
    >({
      query: (params) => {
        const queryString = new URLSearchParams(
          (params as Record<string, string>) ?? {},
        ).toString();
        return queryString
          ? `api/analysis_service?${queryString}`
          : "api/analysis_service";
      },
      providesTags: ["AnalysisServices"],
    }),
    getAnalysisService: build.query<AnalysisService, number | string>({
      query: (id) => `api/analysis_service/${id}`,
      providesTags: ["AnalysisService"],
    }),
    submitAnalysisService: build.mutation<unknown, Record<string, unknown>>({
      query: (run) => ({
        url: "api/analysis_service",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["AnalysisServices"],
    }),
    modifyAnalysisService: build.mutation<unknown, ModifyAnalysisServiceArg>({
      query: ({ id, params }) => ({
        url: `api/analysis_service/${id}`,
        method: "PUT",
        body: params,
      }),
      invalidatesTags: ["AnalysisService", "AnalysisServices"],
    }),
    deleteAnalysisService: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/analysis_service/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["AnalysisService", "AnalysisServices"],
    }),
  }),
});

// Websocket: the old handler refetched the full list on REFRESH_ANALYSIS_SERVICES.
invalidateOnMessage("skyportal/REFRESH_ANALYSIS_SERVICES", () => [
  "AnalysisServices",
]);

export const {
  useGetAnalysisServicesQuery,
  useGetAnalysisServiceQuery,
  useSubmitAnalysisServiceMutation,
  useModifyAnalysisServiceMutation,
  useDeleteAnalysisServiceMutation,
} = analysisServicesApi;
