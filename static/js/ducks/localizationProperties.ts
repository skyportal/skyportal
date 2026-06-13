import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export type LocalizationPropertiesArgs =
  | Record<string, string | number | boolean>
  | undefined;

export const localizationPropertiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getLocalizationProperties: build.query<
      RouteData<"GET /api/localization/properties">,
      LocalizationPropertiesArgs
    >({
      query: (filterParams) => ({
        url: "api/localization/properties",
        params: filterParams ?? {},
      }),
      providesTags: ["LocalizationProperties"],
    }),
  }),
});

export const { useGetLocalizationPropertiesQuery } = localizationPropertiesApi;

// Websocket message handler: refresh localization properties on push.
invalidateOnMessage("skyportal/FETCH_LOCALIZATION_PROPERTIES", () => [
  "LocalizationProperties",
]);
