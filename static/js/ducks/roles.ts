/**
 * Roles (user role definitions).
 *
 * RTK Query conversion of the old `FETCH_ROLES` duck. No websocket, no
 * hydration. The list query provides the `Role` tag; the add/delete mutations
 * affect a user's roles (reflected in the not-yet-migrated users-management
 * slice), so consumers refetch that manually.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface Role {
  id: string;
  acls?: string[] | undefined;
  [key: string]: unknown;
}

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
      query: () => "api/roles",
      providesTags: ["Role"],
    }),
    addUserRoles: build.mutation<unknown, AddUserRolesArg>({
      query: ({ userID, roleIds }) => ({
        url: `api/user/${userID}/roles`,
        method: "POST",
        body: { roleIds },
      }),
    }),
    deleteUserRole: build.mutation<unknown, DeleteUserRoleArg>({
      query: ({ userID, role }) => ({
        url: `api/user/${userID}/roles/${role}`,
        method: "DELETE",
      }),
    }),
  }),
});

export const {
  useGetRolesQuery,
  useAddUserRolesMutation,
  useDeleteUserRoleMutation,
} = rolesApi;
