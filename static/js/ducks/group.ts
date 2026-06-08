/**
 * Single group fetch.
 *
 * RTK Query conversion of the old `FETCH_GROUP` duck. The endpoint is injected
 * into the central `skyportalApi`. The old websocket handler refetched the
 * currently-loaded group on a REFRESH_GROUP message whose `group_id` matched the
 * loaded group; here we invalidate the "Group" tag for that id so the active
 * query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type Group = Record<string, any>;

export const groupApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGroup: build.query<Group, number | string>({
      query: (id) => `api/groups/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Group", id }],
    }),
  }),
});

// Websocket: old handler refetched the loaded group on REFRESH_GROUP when the
// pushed group_id matched.
invalidateOnMessage("skyportal/REFRESH_GROUP", (payload) =>
  payload?.group_id != null ? [{ type: "Group", id: payload.group_id }] : null,
);

export const { useGetGroupQuery } = groupApi;
