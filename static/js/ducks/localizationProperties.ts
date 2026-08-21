import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const localizationPropertiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed filter params
    // that the server ignored.
    getLocalizationProperties: build.query<string[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchLocalizationProperties()),
      providesTags: ["LocalizationProperties"],
    }),
  }),
});

export const { useGetLocalizationPropertiesQuery } = localizationPropertiesApi;

// Websocket message handler: refresh localization properties on push.
invalidateOnMessage("skyportal/FETCH_LOCALIZATION_PROPERTIES", () => [
  "LocalizationProperties",
]);
