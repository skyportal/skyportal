/**
 * Users.
 *
 * RTK Query conversion of the old `FETCH_USER` / `FETCH_USERS` / `PATCH_USER`
 * duck. Endpoints are injected into the central `skyportalApi`. `getUsers`
 * preserves the old slice shape (`{ users, totalMatches }`);
 * `getUserPublicProfile` fetches the profile a user shares with others.
 * `patchUser` is a mutation that invalidates the `User` tag.
 *
 * The websocket `FETCH_USERS` message is bridged to cache invalidation via
 * `invalidateOnMessage`.
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface User {
  id: number;
  username: string;
  [key: string]: unknown;
}

export interface PublicProfile {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  gravatar_url: string;
  is_bot: boolean;
  created_at: string;
  affiliations?: string[];
  bio?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  roles?: string[];
  groups?: string[];
}

export type ActivityKind =
  | "sources_saved"
  | "comments"
  | "classifications"
  | "annotations"
  | "spectra"
  | "followup_requests";

export interface ActivityItem {
  kind: ActivityKind;
  created_at: string;
  obj_id: string | null;
  detail: string | null;
}

/** A user's contributions, limited to what the requester may see. */
export interface UserActivity {
  counts: Record<ActivityKind, number>;
  items: ActivityItem[];
  has_more: boolean;
}

export interface UsersResult {
  users: User[];
  totalMatches: number;
}

export const usersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUsers: build.query<UsersResult, Record<string, any> | void>({
      query: (filterParams) => {
        const params = buildQueryString(
          (filterParams as Record<string, string>) ?? {},
        );
        return `api/user${params ? `?${params}` : ""}`;
      },
      providesTags: ["User"],
    }),
    getUserPublicProfile: build.query<PublicProfile, number | string>({
      query: (id) => `api/user/${id}/profile`,
      providesTags: ["User", "PublicProfile"],
    }),
    getUserActivity: build.query<
      UserActivity,
      { id: number | string; offset?: number; limit?: number }
    >({
      query: ({ id, offset = 0, limit }) =>
        `api/user/${id}/activity?offset=${offset}${limit ? `&limit=${limit}` : ""}`,
      providesTags: ["User", "PublicProfile"],
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

export const {
  useGetUsersQuery,
  useGetUserPublicProfileQuery,
  useGetUserActivityQuery,
  usePatchUserMutation,
} = usersApi;
