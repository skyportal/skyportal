/**
 * User profile (the logged-in user's profile + preferences + tokens).
 *
 * RTK Query conversion of the old `FETCH_USER_PROFILE` duck. The endpoint is
 * injected into the central `skyportalApi`. `getProfile` provides the `Profile`
 * tag; the mutations (preferences, basic info, token create/update/delete)
 * invalidate it so the profile refetches after a change — matching the old
 * behaviour where these thunks triggered a profile refresh.
 *
 * The websocket `FETCH_USER_PROFILE` message is bridged to cache invalidation
 * via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface Profile {
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  gravatar_url?: string;
  affiliations?: any[];
  bio?: string | null;
  oauth_uid?: string | null;
  is_bot?: boolean;
  created_at?: string;
  expiration_date?: string | null;
  streams?: any[];
  permissions: string[];
  acls: string[];
  roles: any[];
  preferences: Record<string, any>;
  groups: any[];
  tokens?: any[];
  groupAdmissionRequests?: any[];
  [key: string]: any;
}

// Deep-merge `source` into `target` (an Immer draft), matching the backend's
// deep merge of preferences, so an optimistic update is correct without a
// refetch.
function deepMergePreferences(target: any, source: any) {
  for (const key of Object.keys(source)) {
    const val = source[key];
    if (
      val &&
      typeof val === "object" &&
      !Array.isArray(val) &&
      target[key] &&
      typeof target[key] === "object" &&
      !Array.isArray(target[key])
    ) {
      deepMergePreferences(target[key], val);
    } else {
      target[key] = val;
    }
  }
}

export const profileApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getProfile: build.query<Profile, void>({
      query: () => "api/internal/profile",
      providesTags: ["Profile"],
    }),
    updateUserPreferences: build.mutation<unknown, any>({
      query: (preferences) => ({
        url: "api/internal/profile",
        method: "PATCH",
        body: { preferences },
      }),
      // Optimistically merge the new preferences into the cached profile instead
      // of invalidating "Profile": that blanket refetch re-renders the ~89
      // components reading the profile on every settings change, which churns
      // the dashboard. Revert if the request fails.
      async onQueryStarted(preferences, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          profileApi.util.updateQueryData("getProfile", undefined, (draft) => {
            if (!(draft as any).preferences) (draft as any).preferences = {};
            deepMergePreferences((draft as any).preferences, preferences);
          }),
        );
        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
    }),
    updateBasicUserInfo: build.mutation<
      unknown,
      { formData: any; user_id?: number | string }
    >({
      query: ({ formData, user_id }) => ({
        url: `api/internal/profile${user_id ? `/${user_id}` : ""}`,
        method: "PATCH",
        body: formData,
      }),
      invalidatesTags: ["Profile"],
    }),
    createToken: build.mutation<unknown, any>({
      query: (form_data) => ({
        url: "api/internal/tokens",
        method: "POST",
        body: form_data,
      }),
      invalidatesTags: ["Profile"],
    }),
    updateToken: build.mutation<
      unknown,
      { tokenID: number | string; form_data: any }
    >({
      query: ({ tokenID, form_data }) => ({
        url: `api/internal/tokens/${tokenID}`,
        method: "PUT",
        body: form_data,
      }),
      invalidatesTags: ["Profile"],
    }),
    deleteToken: build.mutation<unknown, number | string>({
      query: (tokenID) => ({
        url: `api/internal/tokens/${tokenID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Profile"],
    }),
  }),
});

// Websocket-driven invalidation: refresh the profile on FETCH_USER_PROFILE.
invalidateOnMessage("skyportal/FETCH_USER_PROFILE", () => ["Profile"]);

export const {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
  useUpdateBasicUserInfoMutation,
  useCreateTokenMutation,
  useUpdateTokenMutation,
  useDeleteTokenMutation,
} = profileApi;
