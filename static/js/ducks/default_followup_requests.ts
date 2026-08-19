/**
 * Default followup requests.
 *
 * RTK Query conversion of the old `FETCH_DEFAULT_FOLLOWUP_REQUESTS` duck.
 * Websocket-driven invalidation refetches the request list; mutations
 * submit/delete a default followup request.
 */
import type {
  DefaultFollowupRequest,
  DefaultFollowupRequestPost,
} from "skyportal-js/FollowupRequests";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const defaultFollowupRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDefaultFollowupRequests: build.query<DefaultFollowupRequest[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchDefaultFollowupRequests()),
      providesTags: ["DefaultFollowupRequest"],
    }),
    submitDefaultFollowupRequest: build.mutation<
      { id: number },
      DefaultFollowupRequestPost
    >({
      queryFn: (default_plan, api) =>
        clientQuery(api, (client) =>
          client.postDefaultFollowupRequest(default_plan),
        ),
      invalidatesTags: ["DefaultFollowupRequest"],
    }),
    deleteDefaultFollowupRequest: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.deleteDefaultFollowupRequest(Number(id)),
        ),
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
