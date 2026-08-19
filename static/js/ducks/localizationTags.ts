/**
 * Localization tags (the set of tag strings attached to localizations).
 *
 * RTK Query conversion of the old `FETCH_LOCALIZATION_TAGS` duck, calling the
 * typed `skyportal-js` client; the websocket refresh message is bridged to
 * cache invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type LocalizationTags = string[];

export const localizationTagsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed filter params
    // that the server ignored.
    getLocalizationTags: build.query<LocalizationTags, void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchLocalizationTags()),
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
