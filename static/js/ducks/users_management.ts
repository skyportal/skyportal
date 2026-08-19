/**
 * Users management (the admin "Manage Users" table).
 *
 * The table is small enough to be paginated, sorted and
 * filtered client-side by the DataGrid, so this query fetches every user in one
 * go (no `numPerPage`). `includeExpired` stays server-side: it widens which
 * users are returned, it is not a display filter.
 *
 * The websocket `FETCH_USERS_MANAGEMENT` message is bridged to cache
 * invalidation via `invalidateOnMessage`, so the active query refetches.
 */
import type { FetchUsersOptions, UsersPage } from "skyportal-js/Users";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type UsersManagementParams = FetchUsersOptions;
export type UsersManagementResult = UsersPage;

export const usersManagementApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUsersManagement: build.query<UsersPage, UsersManagementParams | void>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.fetchUsers(params ?? {})),
      providesTags: ["UserManagement"],
    }),
  }),
});

// Websocket-driven invalidation: refresh the users-management table on the
// backend's FETCH_USERS_MANAGEMENT push. Only the active query refetches.
invalidateOnMessage("skyportal/FETCH_USERS_MANAGEMENT", () => [
  "UserManagement",
]);

export const { useGetUsersManagementQuery } = usersManagementApi;
