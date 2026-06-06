/**
 * Default followup requests.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_FOLLOWUP_REQUESTS` duck.
 * Websocket-driven invalidation refetches the request list; mutations
 * submit/delete a default followup request.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const defaultFollowupRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultFollowupRequests: build.query<any[], void>({
      query: () => "api/default_followup_request",
      providesTags: ["DefaultFollowupRequest"],
    }),
    submitDefaultFollowupRequest: build.mutation<unknown, any>({
      query: (default_plan) => ({
        url: "api/default_followup_request",
        method: "POST",
        body: default_plan,
      }),
      invalidatesTags: ["DefaultFollowupRequest"],
    }),
    deleteDefaultFollowupRequest: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/default_followup_request/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["DefaultFollowupRequest"],
    }),
  }),
});

// Websocket: the old handler refetched the full list on
// REFRESH_DEFAULT_FOLLOWUP_REQUESTS.
invalidateOnMessage("skyportal/REFRESH_DEFAULT_FOLLOWUP_REQUESTS", () => [
  "DefaultFollowupRequest",
]);

export const {
  useGetDefaultFollowupRequestsQuery,
  useSubmitDefaultFollowupRequestMutation,
  useDeleteDefaultFollowupRequestMutation,
} = defaultFollowupRequestsApi;
