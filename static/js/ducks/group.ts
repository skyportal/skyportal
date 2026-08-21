/**
 * Single group fetch.
 *
 * RTK Query conversion of the old `FETCH_GROUP` duck, calling the typed
 * `skyportal-js` client. The old websocket handler refetched the
 * currently-loaded group on a REFRESH_GROUP message whose `group_id` matched the
 * loaded group; here we invalidate the "Group" tag for that id so the active
 * query refetches.
 */
import type { Group } from "skyportal-js/Groups";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const groupApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGroup: build.query<Group, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchGroup(Number(id))),
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
