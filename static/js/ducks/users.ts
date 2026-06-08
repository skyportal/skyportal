/**
 * Users.
 *
 * RTK Query conversion of the old `FETCH_USER` / `FETCH_USERS` / `PATCH_USER`
 * duck. Endpoints are injected into the central `skyportalApi`. `getUsers`
 * preserves the old slice shape (`{ users, totalMatches }`); `getUser` fetches a
 * single user. `patchUser` is a mutation that invalidates the `User` tag.
 *
 * The websocket `FETCH_USERS` message is bridged to cache invalidation via
 * `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface User {
  id: number;
  username: string;
  [key: string]: unknown;
}

export interface UsersResult {
  users: User[];
  totalMatches: number;
}

export const usersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUsers: build.query<UsersResult, Record<string, any> | void>({
      query: (filterParams) => {
        const params = new URLSearchParams(
          filterParams as Record<string, string> | undefined,
        ).toString();
        return `api/user${params ? `?${params}` : ""}`;
      },
      providesTags: ["User"],
    }),
    getUser: build.query<User, number | string>({
      query: (id) => `api/user/${id}`,
      providesTags: ["User"],
    }),
    patchUser: build.mutation<
      unknown,
      { id: number | string; data: Record<string, any> }
    >({
      query: ({ id, data }) => ({
        url: `api/user/${id}`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["User"],
    }),
  }),
});

// Websocket-driven invalidation: refresh users on FETCH_USERS.
invalidateOnMessage("skyportal/FETCH_USERS", () => ["User"]);

export const { useGetUsersQuery, useGetUserQuery, usePatchUserMutation } =
  usersApi;
