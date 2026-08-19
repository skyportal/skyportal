/**
 * Analysis services.
 *
 * RTK Query conversion of the old `FETCH_ANALYSIS_SERVICES_LIST` /
 * `FETCH_ANALYSIS_SERVICE` duck. The list query feeds the analysis service
 * pages and dropdowns; mutations submit/modify/delete a service. The websocket
 * `REFRESH_ANALYSIS_SERVICES` message is bridged to cache invalidation via
 * `invalidateOnMessage`.
 */
import type {
  AnalysisService,
  AnalysisServicePost,
  AnalysisServiceUpdate,
} from "skyportal-js/Analysis";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface ModifyAnalysisServiceArg {
  id: number | string;
  params: AnalysisServiceUpdate;
}

export const analysisServicesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed params that
    // the server ignored.
    getAnalysisServices: build.query<AnalysisService[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchAnalysisServices()),
      providesTags: ["AnalysisServices"],
    }),
    getAnalysisService: build.query<AnalysisService, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchAnalysisService(Number(id))),
      providesTags: ["AnalysisService"],
    }),
    submitAnalysisService: build.mutation<{ id: number }, AnalysisServicePost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postAnalysisService(run)),
      invalidatesTags: ["AnalysisServices"],
    }),
    // PATCH, not PUT: the handler implements no put(), so the old request was
    // answered with 405.
    modifyAnalysisService: build.mutation<void, ModifyAnalysisServiceArg>({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.updateAnalysisService(Number(id), params),
        ),
      invalidatesTags: ["AnalysisService", "AnalysisServices"],
    }),
    deleteAnalysisService: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteAnalysisService(Number(id))),
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
