/**
 * Roles (user role definitions).
 *
 * RTK Query conversion of the old `FETCH_ROLES` duck, calling the typed
 * `skyportal-js` client. No websocket, no hydration. The list query provides the
 * `Role` tag; the add/delete mutations affect a user's roles (reflected in the
 * not-yet-migrated users-management slice), so consumers refetch that manually.
 */
import type { Role } from "skyportal-js/Roles";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

interface AddUserRolesArg {
  userID: number | string;
  roleIds: string[];
}

interface DeleteUserRoleArg {
  userID: number | string;
  role: string;
}

export const rolesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRoles: build.query<Role[], void>({
      queryFn: (_arg, api) => clientQuery(api, (client) => client.fetchRoles()),
      providesTags: ["Role"],
    }),
    addUserRoles: build.mutation<void, AddUserRolesArg>({
      queryFn: ({ userID, roleIds }, api) =>
        clientQuery(api, (client) =>
          client.postUserRole(Number(userID), roleIds),
        ),
    }),
    deleteUserRole: build.mutation<void, DeleteUserRoleArg>({
      queryFn: ({ userID, role }, api) =>
        clientQuery(api, (client) =>
          client.deleteUserRole(Number(userID), role),
        ),
    }),
  }),
});

export const {
  useGetRolesQuery,
  useAddUserRolesMutation,
  useDeleteUserRoleMutation,
} = rolesApi;
