/**
 * Users management (the admin "Manage Users" table).
 *
 * The table is small enough to be paginated, sorted and
 * filtered client-side by the DataGrid, so this query fetches every user in one
 * go. `includeExpired` stays server-side: it widens which users are returned,
 * it is not a display filter.
 *
 * The websocket `FETCH_USERS_MANAGEMENT` message is bridged to cache
 * invalidation via `invalidateOnMessage`, so the active query refetches.
 */
import { buildQueryString as toQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface UsersManagementParams {
  includeExpired?: boolean | undefined;
  [key: string]: string | number | boolean | undefined;
}

export interface UsersManagementResult {
  users: any[];
  totalMatches: number;
}

export const usersManagementApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUsersManagement: build.query<
      UsersManagementResult,
      UsersManagementParams | void
    >({
      query: (params) => {
        const qs = toQueryString(params ?? {});
        return `api/user${qs ? `?${qs}` : ""}`;
      },
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
