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
      invalidatesTags: ["Profile"],
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
