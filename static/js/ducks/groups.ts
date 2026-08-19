/**
 * Groups (the list of groups visible to the current user).
 *
 * RTK Query conversion of the old `FETCH_GROUPS` duck, calling the typed
 * `skyportal-js` client. The backend returns
 * `{ user_groups, user_accessible_groups, all_groups }`; the query keeps the old
 * slice shape (`{ user, userAccessible, all }`) consumers expect. The various
 * group/group-user create/update/delete actions are mutations that invalidate
 * the `Group` tag so the list refetches.
 *
 * The websocket `skyportal/FETCH_GROUPS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import type { Group, GroupPost } from "skyportal-js/Groups";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface GroupsResult {
  user: Group[];
  userAccessible: Group[];
  all: Group[] | null;
}

export const groupsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGroups: build.query<GroupsResult, void>({
      queryFn: (_arg, api) =>
        clientQuery(api, async (client) => {
          const data = await client.fetchGroups({
            includeSingleUserGroups: true,
          });
          return {
            user: data.user_groups,
            userAccessible: data.user_accessible_groups,
            all: data.all_groups ?? null,
          };
        }),
      providesTags: ["Group"],
    }),
    addNewGroup: build.mutation<{ id: number }, GroupPost>({
      queryFn: (form_data, api) =>
        clientQuery(api, (client) => client.postGroup(form_data)),
      invalidatesTags: ["Group"],
    }),
    // raw: the client's updateGroup types nickname/description as strings, but
    // this form clears them with an explicit null.
    updateGroup: build.mutation<
      unknown,
      { group_id: number | string; form_data: Record<string, unknown> }
    >({
      query: ({ group_id, form_data }) => ({
        url: `api/groups/${group_id}`,
        method: "PUT",
        body: form_data,
      }),
      invalidatesTags: ["Group"],
    }),
    deleteGroup: build.mutation<void, number | string>({
      queryFn: (group_id, api) =>
        clientQuery(api, (client) => client.deleteGroup(Number(group_id))),
      invalidatesTags: ["Group"],
    }),
    addGroupUser: build.mutation<
      { group_id: number; user_id: number },
      {
        userID: number | string;
        admin: boolean;
        group_id: number | string;
        canSave: boolean;
        canSharePhotometry: boolean;
      }
    >({
      queryFn: (
        { userID, admin, group_id, canSave, canSharePhotometry },
        api,
      ) =>
        clientQuery(api, (client) =>
          client.postGroupUser(Number(group_id), Number(userID), {
            admin,
            canSave,
            canSharePhotometry,
          }),
        ),
      invalidatesTags: ["Group"],
    }),
    addAllUsersFromGroups: build.mutation<
      void,
      { toGroupID: number | string; fromGroupIDs: (number | string)[] }
    >({
      queryFn: ({ toGroupID, fromGroupIDs }, api) =>
        clientQuery(api, (client) =>
          client.postGroupUsersFromGroups(
            Number(toGroupID),
            fromGroupIDs.map(Number),
          ),
        ),
      invalidatesTags: ["Group"],
    }),
    updateGroupUser: build.mutation<
      void,
      {
        groupID: number | string;
        params: {
          userID: number | string;
          admin?: boolean;
          canSave?: boolean;
          canSharePhotometry?: boolean;
        };
      }
    >({
      queryFn: ({ groupID, params: { userID, ...flags } }, api) =>
        clientQuery(api, (client) =>
          client.updateGroupUser(Number(groupID), Number(userID), flags),
        ),
      invalidatesTags: ["Group"],
    }),
    deleteGroupUser: build.mutation<
      void,
      { userID: number | string; group_id: number | string }
    >({
      queryFn: ({ userID, group_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteGroupUser(Number(group_id), Number(userID)),
        ),
      invalidatesTags: ["Group"],
    }),
  }),
});

// Websocket-driven invalidation: refresh groups on skyportal/FETCH_GROUPS.
invalidateOnMessage("skyportal/FETCH_GROUPS", () => ["Group"]);

export const {
  useGetGroupsQuery,
  useAddNewGroupMutation,
  useUpdateGroupMutation,
  useDeleteGroupMutation,
  useAddGroupUserMutation,
  useAddAllUsersFromGroupsMutation,
  useUpdateGroupUserMutation,
  useDeleteGroupUserMutation,
} = groupsApi;
