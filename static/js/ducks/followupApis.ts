/**
 * Followup API configurations.
 *
 * RTK Query conversion of the old `FETCH_FOLLOWUP_APIS` duck. The endpoint
 * returns the available followup API classnames keyed by classname (each with a
 * `formSchemaConfig`). The old websocket handler refetched the list on a
 * REFRESH_FOLLOWUP_APIS message; here we invalidate the "FollowupApi" tag so
 * the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type FollowupApis = Record<string, any>;

export const followupApisApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFollowupApis: build.query<FollowupApis, void>({
      query: () => "api/internal/followup_apis",
      providesTags: ["FollowupApi"],
    }),
  }),
});

// Websocket: old handler refetched the followup APIs on REFRESH_FOLLOWUP_APIS.
invalidateOnMessage("skyportal/REFRESH_FOLLOWUP_APIS", () => ["FollowupApi"]);

export const { useGetFollowupApisQuery } = followupApisApi;
