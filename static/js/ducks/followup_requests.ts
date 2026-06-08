/**
 * Follow-up requests.
 *
 * RTK Query conversion of the old `FETCH_FOLLOWUP_REQUESTS` duck. The list is a
 * paginated query keyed on the fetch params; mutations watch/unwatch a request
 * and (re-)prioritize requests. The websocket `REFRESH_FOLLOWUP_REQUESTS`
 * message is bridged to cache invalidation via `invalidateOnMessage`.
 *
 * The schedule/allocation-report downloads remain plain redux-thunks that stream
 * a file to the browser (they are side-effecting blob fetches, not cacheable
 * data, so they do not fit the query/mutation model).
 */
import * as API from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import { filterOutEmptyValues } from "../API";

interface FollowupRequestsResult {
  followup_requests: any[];
  totalMatches: number;
  [key: string]: unknown;
}

type FollowupRequestsArg = Record<string, any> | void;

const buildFollowupRequestsUrl = (params: Record<string, any>): string => {
  const withDefaults = { ...params };
  if (!Object.keys(withDefaults).includes("numPerPage")) {
    withDefaults["numPerPage"] = 10;
  }
  const filtered = filterOutEmptyValues(withDefaults);
  const queryString = new URLSearchParams(
    filtered as Record<string, string>,
  ).toString();
  return queryString
    ? `api/followup_request?${queryString}`
    : "api/followup_request";
};

export const followupRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFollowupRequests: build.query<
      FollowupRequestsResult,
      FollowupRequestsArg
    >({
      query: (params) => buildFollowupRequestsUrl(params ?? {}),
      providesTags: ["FollowupRequest"],
    }),
    prioritizeFollowupRequests: build.mutation<unknown, Record<string, any>>({
      query: (body) => ({
        url: "api/followup_request/prioritization",
        method: "PUT",
        body,
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

// Plain thunks for browser file downloads (not part of the RTK Query cache).
export const downloadFollowupSchedule = (
  instrumentId: number | string,
  format = "csv",
  include_standards = false,
) =>
  API.DOWNLOAD(
    `/api/followup_request/schedule/${instrumentId}`,
    "skyportal/DOWNLOAD_FOLLOWUP_SCHEDULE",
    {
      output_format: format, // ensure the format is passed in the URL
      includeStandards: include_standards, // include standards if specified
      filename: `followup_schedule_${instrumentId}.${format.toLowerCase()}`, // filename for the download
    },
  );

export const downloadAllocationReport = (instrumentId: number | string) =>
  API.DOWNLOAD(
    `/api/allocation/report/${instrumentId}`,
    "skyportal/DOWNLOAD_ALLOCATION_REPORT",
    {},
  );

// Websocket: the old handler refetched the list on REFRESH_FOLLOWUP_REQUESTS.
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
