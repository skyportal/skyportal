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
import type { ProfilePatch, UserProfile } from "skyportal-js/Profile";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

/**
 * The logged-in user's profile, as modelled by the client, with `preferences`
 * left as free-form `any`: it is an open JSON blob that many components index
 * into, and `unknown` values would need a cast at each of them.
 */
export type Profile = Omit<UserProfile, "preferences" | "id"> & {
  id: number;
  preferences: Record<string, any>;
};

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
      queryFn: (_arg, api) =>
        // The client types `id` as optional; the column is NOT NULL and the
        // handler serializes the whole user, so it is always present
        // (skyportal-js#6 tightens the model).
        clientQuery(
          api,
          async (client) => (await client.fetchProfile()) as Profile,
        ),
      providesTags: ["Profile"],
    }),
    updateUserPreferences: build.mutation<void, Record<string, unknown>>({
      queryFn: (preferences, api) =>
        clientQuery(api, (client) => client.updateProfile({ preferences })),
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
      void,
      { formData: ProfilePatch; user_id?: number | string }
    >({
      queryFn: ({ formData, user_id }, api) =>
        clientQuery(api, (client) =>
          client.updateProfile(
            formData,
            user_id ? { userId: Number(user_id) } : {},
          ),
        ),
      invalidatesTags: ["Profile"],
    }),
    createToken: build.mutation<
      { token_id: string },
      { name: string; acls: string[] }
    >({
      queryFn: ({ name, acls }, api) =>
        clientQuery(api, (client) => client.postToken(name, acls)),
      invalidatesTags: ["Profile"],
    }),
    updateToken: build.mutation<
      void,
      {
        tokenID: number | string;
        form_data: { name?: string; acls?: string[] };
      }
    >({
      queryFn: ({ tokenID, form_data }, api) =>
        clientQuery(api, (client) =>
          client.updateToken(String(tokenID), form_data),
        ),
      invalidatesTags: ["Profile"],
    }),
    deleteToken: build.mutation<void, number | string>({
      queryFn: (tokenID, api) =>
        clientQuery(api, (client) => client.deleteToken(String(tokenID))),
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

// True when the current request is served as the read-only anonymous account.
// Drives the login-vs-account UI (a logged-in "View only" user is NOT anonymous).
export const useIsAnonymous = (): boolean =>
  !!useGetProfileQuery().data?.is_anonymous;

// True for any user with no write ACLs (the anonymous account AND logged-in
// "View only" users). Use to hide write/action UI that isn't already gated on a
// specific ACL. Defaults to read-only while the profile is loading.
export const useIsReadOnly = (): boolean =>
  (useGetProfileQuery().data?.permissions?.length ?? 0) === 0;
