/**
 * Localization tags (the set of tag strings attached to localizations).
 *
 * RTK Query conversion of the old `FETCH_LOCALIZATION_TAGS` duck. The endpoint
 * is injected into the central `skyportalApi`; the websocket refresh message is
 * bridged to cache invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type LocalizationTags = string[];

export interface LocalizationTagsArg {
  [key: string]: unknown;
}

export const localizationTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getLocalizationTags: build.query<
      LocalizationTags,
      LocalizationTagsArg | void
    >({
      query: (filterParams) => {
        const params = new URLSearchParams(
          (filterParams as Record<string, string>) || {},
        ).toString();
        return params
          ? `api/localization/tags?${params}`
          : "api/localization/tags";
      },
      providesTags: ["LocalizationTag"],
    }),
  }),
});

export const { useGetLocalizationTagsQuery } = localizationTagsApi;

// Websocket-driven invalidation: refresh the localization tags on the
// corresponding refresh message.
invalidateOnMessage("skyportal/FETCH_LOCALIZATION_TAGS", () => [
  "LocalizationTag",
]);
