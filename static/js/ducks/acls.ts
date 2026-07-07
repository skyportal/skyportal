/**
 * ACLs (access control lists).
 *
 * RTK Query conversion of the old `FETCH_ACLS` duck. No websocket, no hydration.
 */
import { skyportalApi } from "../api/skyportalApi";

export type Acls = string[];

interface AddUserAclsArg {
  userID: number | string;
  aclIds: string[];
}

interface DeleteUserAclArg {
  userID: number | string;
  acl: string;
}

export const aclsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAcls: build.query<Acls, void>({
      query: () => "api/acls",
      providesTags: ["Acls"],
    }),
    addUserAcls: build.mutation<unknown, AddUserAclsArg>({
      query: ({ userID, aclIds }) => ({
        url: `api/user/${userID}/acls`,
        method: "POST",
        body: { aclIds },
      }),
    }),
    deleteUserAcl: build.mutation<unknown, DeleteUserAclArg>({
      query: ({ userID, acl }) => ({
        url: `api/user/${userID}/acls/${acl}`,
        method: "DELETE",
      }),
    }),
  }),
});

export const {
  useGetAclsQuery,
  useAddUserAclsMutation,
  useDeleteUserAclMutation,
} = aclsApi;
