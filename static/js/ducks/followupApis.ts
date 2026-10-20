/**
 * Followup API configurations.
 *
 * RTK Query conversion of the old `FETCH_FOLLOWUP_APIS` duck. The endpoint
 * returns the available followup API classnames keyed by classname (each with a
 * `formSchemaConfig`).
 */
import { skyportalApi } from "../api/skyportalApi";

export type FollowupApis = Record<string, any>;

export const followupApisApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFollowupApis: build.query<FollowupApis, void>({
      query: () => "api/internal/followup_apis",
      providesTags: ["FollowupApi"],
    }),
  }),
});

export const { useGetFollowupApisQuery } = followupApisApi;
