import * as API from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import { buildQueryString, filterOutEmptyValues } from "../API";
import type { RouteData } from "../types/routeSchemaMap";

type FollowupRequestsArg = Record<string, any> | void;

const buildFollowupRequestsUrl = (params: Record<string, any>): string => {
  const withDefaults = { ...params };
  if (!Object.keys(withDefaults).includes("numPerPage")) {
    withDefaults["numPerPage"] = 25;
  }
  // keep false so includeObjThumbnails=false actually reaches the server
  const filtered = filterOutEmptyValues(withDefaults, true, false);
  const queryString = buildQueryString(filtered);
  return queryString
    ? `api/followup_request?${queryString}`
    : "api/followup_request";
};

export const followupRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFollowupRequests: build.query<
      RouteData<"GET /api/followup_request">,
      FollowupRequestsArg
    >({
      query: (params) => buildFollowupRequestsUrl(params ?? {}),
      providesTags: ["FollowupRequest"],
    }),
    prioritizeFollowupRequests: build.mutation<
      RouteData<"PUT /api/followup_request/prioritization">,
      Record<string, any>
    >({
      // The endpoint forbids unknown keys, so drop the form's UI-only fields.
      query: ({
        requestIds,
        priorityType,
        magnitudeOrdering,
        localizationId,
        minimumPriority,
        maximumPriority,
      }) => ({
        url: "api/followup_request/prioritization",
        method: "PUT",
        body: {
          requestIds,
          priorityType,
          magnitudeOrdering,
          localizationId,
          minimumPriority,
          maximumPriority,
        },
      }),
      invalidatesTags: ["FollowupRequest"],
    }),
    addToWatchList: build.mutation<
      unknown,
      { id: number | string; params?: Record<string, any> }
    >({
      query: ({ id, params = {} }) => ({
        url: `api/followup_request/watch/${id}`,
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["FollowupRequest"],
    }),
    removeFromWatchList: build.mutation<
      unknown,
      { id: number | string; params?: Record<string, any> }
    >({
      query: ({ id, params = {} }) => ({
        url: `api/followup_request/watch/${id}`,
        method: "DELETE",
        body: params,
      }),
      invalidatesTags: ["FollowupRequest"],
    }),
  }),
});

export const downloadFollowupSchedule = (
  instrumentId: number | string,
  format = "csv",
  include_standards = false,
) =>
  // DOWNLOAD does not send its payload, so the query params go in the URL.
  API.DOWNLOAD(
    `/api/followup_request/schedule/${instrumentId}?${buildQueryString({
      output_format: format,
      includeStandards: include_standards,
    })}`,
    "skyportal/DOWNLOAD_FOLLOWUP_SCHEDULE",
    {
      filename: `followup_schedule_${instrumentId}.${format.toLowerCase()}`,
    },
  );

export const downloadAllocationReport = (instrumentId: number | string) =>
  API.DOWNLOAD(
    `/api/allocation/report/${instrumentId}`,
    "skyportal/DOWNLOAD_ALLOCATION_REPORT",
    {},
  );

invalidateOnMessage("skyportal/REFRESH_FOLLOWUP_REQUESTS", () => [
  "FollowupRequest",
]);

export const {
  useGetFollowupRequestsQuery,
  useLazyGetFollowupRequestsQuery,
  usePrioritizeFollowupRequestsMutation,
  useAddToWatchListMutation,
  useRemoveFromWatchListMutation,
} = followupRequestsApi;
