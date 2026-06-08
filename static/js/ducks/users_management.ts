/**
 * Users management (the admin "Manage Users" table).
 *
 * RTK Query conversion of the old `FETCH_USERS_MANAGEMENT` duck. The query
 * accepts the filter/pagination/sort parameters as its argument (the old duck
 * stashed these in a `fetchParams` slice; consumers now own that state and pass
 * it in). The backend's `GET /api/user` returns `{ users, totalMatches }`.
 *
 * The websocket `FETCH_USERS_MANAGEMENT` message is bridged to cache
 * invalidation via `invalidateOnMessage`, so the active query refetches with
 * whatever params it currently holds.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface UsersManagementParams {
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
  sortBy?: string | undefined;
  sortOrder?: string | undefined;
  includeExpired?: boolean | undefined;
  firstName?: string | undefined;
  lastName?: string | undefined;
  username?: string | undefined;
  affiliations?: string | undefined;
  email?: string | undefined;
  role?: string | undefined;
  acl?: string | undefined;
  group?: string | undefined;
  stream?: string | undefined;
  [key: string]: string | number | boolean | undefined;
}

export interface UsersManagementResult {
  users: any[];
  totalMatches: number;
}

const buildQueryString = (params: UsersManagementParams): string => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.append(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
};

export const usersManagementApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUsersManagement: build.query<
      UsersManagementResult,
      UsersManagementParams | void
    >({
      query: (params) => {
        const filterParams: UsersManagementParams = {
          pageNumber: 1,
          numPerPage: 25,
          ...(params ?? {}),
        };
        return `api/user${buildQueryString(filterParams)}`;
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
