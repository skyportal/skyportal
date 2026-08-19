/**
 * Users management (the admin "Manage Users" table).
 *
 * RTK Query conversion of the old `FETCH_USERS_MANAGEMENT` duck, calling the
 * typed `skyportal-js` client. The query accepts the filter/pagination/sort
 * parameters as its argument (the old duck stashed these in a `fetchParams`
 * slice; consumers now own that state and pass it in). The backend's
 * `GET /api/user` returns `{ users, totalMatches }`.
 *
 * The websocket `FETCH_USERS_MANAGEMENT` message is bridged to cache
 * invalidation via `invalidateOnMessage`, so the active query refetches with
 * whatever params it currently holds.
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
        clientQuery(api, (client) =>
          client.fetchUsers({
            pageNumber: 1,
            numPerPage: 25,
            ...(params ?? {}),
          }),
        ),
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
