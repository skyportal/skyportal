/**
 * Users.
 *
 * RTK Query conversion of the old `FETCH_USER` / `FETCH_USERS` / `PATCH_USER`
 * duck, calling the typed `skyportal-js` client. `getUsers` preserves the old
 * slice shape (`{ users, totalMatches }`); `getUser` fetches a single user.
 * `patchUser` is a mutation that invalidates the `User` tag.
 *
 * The websocket `FETCH_USERS` message is bridged to cache invalidation via
 * `invalidateOnMessage`.
 */
import type { FetchUsersOptions, User, UsersPage } from "skyportal-js/Users";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type { User };
export type UsersResult = UsersPage;

export const usersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUsers: build.query<UsersPage, FetchUsersOptions | void>({
      queryFn: (filterParams, api) =>
        clientQuery(api, (client) => client.fetchUsers(filterParams ?? {})),
      providesTags: ["User"],
    }),
    getUser: build.query<User, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchUser(Number(id))),
      providesTags: ["User"],
    }),
    // raw: the client's updateUser only models `expirationDate`, but the
    // handler assigns any non-protected column (this patches names, username
    // and contact_email too).
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
