/**
 * Localization tags (the set of tag strings attached to localizations).
 *
 * RTK Query conversion of the old `FETCH_LOCALIZATION_TAGS` duck. The endpoint
 * is injected into the central `skyportalApi`.
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";

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
        const params = buildQueryString(filterParams || {});
        return params
          ? `api/localization/tags?${params}`
          : "api/localization/tags";
      },
      providesTags: ["LocalizationTag"],
    }),
  }),
});

export const { useGetLocalizationTagsQuery } = localizationTagsApi;
