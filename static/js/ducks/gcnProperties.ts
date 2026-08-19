/**
 * GCN event properties (list of available property names for filtering).
 *
 * RTK Query conversion of the old `FETCH_GCN_PROPERTIES` duck, calling the typed
 * `skyportal-js` client. The websocket refresh message
 * (`skyportal/FETCH_GCN_PROPERTIES`) is bridged to cache invalidation via
 * `invalidateOnMessage`; the old handler ignored the payload and always
 * refreshed, so we unconditionally invalidate the `GcnProperties` tag.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const gcnPropertiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed filter params
    // that the server ignored.
    getGcnProperties: build.query<string[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchGcnEventProperties()),
      providesTags: ["GcnProperties"],
    }),
  }),
});

// Bridge the websocket refresh message to cache invalidation. The old handler
// always re-fetched on this actionType regardless of payload.
invalidateOnMessage("skyportal/FETCH_GCN_PROPERTIES", () => ["GcnProperties"]);

export const { useGetGcnPropertiesQuery } = gcnPropertiesApi;
