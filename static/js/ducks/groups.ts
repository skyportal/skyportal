/**
 * Groups (the list of groups visible to the current user).
 *
 * RTK Query conversion of the old `FETCH_GROUPS` duck. The endpoint is injected
 * into the central `skyportalApi`. The backend returns
 * `{ user_groups, user_accessible_groups, all_groups }`; the query keeps the old
 * slice shape (`{ user, userAccessible, all }`) consumers expect. The various
 * group/group-user create/update/delete actions are mutations that invalidate
 * the `Group` tag so the list refetches.
 *
 * The websocket `skyportal/FETCH_GROUPS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface Group {
  id: number;
  name: string;
  [key: string]: unknown;
}

interface GroupsResult {
  user: Group[];
  userAccessible: Group[];
  all: Group[] | null;
}

interface GroupsResponse {
  user_groups: Group[];
  user_accessible_groups: Group[];
  all_groups: Group[] | null;
}

export const groupsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGroups: build.query<GroupsResult, void>({
      query: () => "api/groups?includeSingleUserGroups=true",
      transformResponse: (data: GroupsResponse) => ({
        user: data?.user_groups ?? [],
        userAccessible: data?.user_accessible_groups ?? [],
        all: data?.all_groups ?? null,
      }),
      providesTags: ["Group"],
    }),
    addNewGroup: build.mutation<unknown, Record<string, unknown>>({
      query: (form_data) => ({
        url: "api/groups",
        method: "POST",
        body: form_data,
      }),
      invalidatesTags: ["Group"],
    }),
    deleteGroup: build.mutation<unknown, number | string>({
      query: (group_id) => ({
        url: `api/groups/${group_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Group"],
    }),
    addGroupUser: build.mutation<
      unknown,
      {
        userID: number | string;
        admin: boolean;
        group_id: number | string;
        canSave: boolean;
      }
    >({
      query: ({ userID, admin, group_id, canSave }) => ({
        url: `api/groups/${group_id}/users`,
        method: "POST",
        body: { userID, admin, group_id, canSave },
      }),
      invalidatesTags: ["Group"],
    }),
    addAllUsersFromGroups: build.mutation<
      unknown,
      { toGroupID: number | string; fromGroupIDs: (number | string)[] }
    >({
      query: ({ toGroupID, fromGroupIDs }) => ({
        url: `api/groups/${toGroupID}/usersFromGroups`,
        method: "POST",
        body: { fromGroupIDs },
      }),
      invalidatesTags: ["Group"],
    }),
    updateGroupUser: build.mutation<
      unknown,
      { groupID: number | string; params: Record<string, unknown> }
    >({
      query: ({ groupID, params }) => ({
        url: `api/groups/${groupID}/users`,
        method: "PATCH",
        body: params,
      }),
      invalidatesTags: ["Group"],
    }),
    deleteGroupUser: build.mutation<
      unknown,
      { userID: number | string; group_id: number | string }
    >({
      query: ({ userID, group_id }) => ({
        url: `api/groups/${group_id}/users/${userID}`,
        method: "DELETE",
        body: { userID, group_id },
      }),
      invalidatesTags: ["Group"],
    }),
  }),
});

// Websocket-driven invalidation: refresh groups on skyportal/FETCH_GROUPS.
invalidateOnMessage("skyportal/FETCH_GROUPS", () => ["Group"]);

export const {
  useGetGroupsQuery,
  useAddNewGroupMutation,
  useDeleteGroupMutation,
  useAddGroupUserMutation,
  useAddAllUsersFromGroupsMutation,
  useUpdateGroupUserMutation,
  useDeleteGroupUserMutation,
} = groupsApi;
