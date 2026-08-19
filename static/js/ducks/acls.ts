/**
 * ACLs (access control lists).
 *
 * RTK Query conversion of the old `FETCH_ACLS` duck. No websocket, no hydration.
 * Endpoints call the typed `skyportal-js` client.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

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
      queryFn: (_arg, api) => clientQuery(api, (client) => client.fetchAcls()),
      providesTags: ["Acls"],
    }),
    addUserAcls: build.mutation<void, AddUserAclsArg>({
      queryFn: ({ userID, aclIds }, api) =>
        clientQuery(api, (client) =>
          client.postUserAcl(Number(userID), aclIds),
        ),
    }),
    deleteUserAcl: build.mutation<void, DeleteUserAclArg>({
      queryFn: ({ userID, acl }, api) =>
        clientQuery(api, (client) => client.deleteUserAcl(Number(userID), acl)),
    }),
  }),
});

export const {
  useGetAclsQuery,
  useAddUserAclsMutation,
  useDeleteUserAclMutation,
} = aclsApi;
