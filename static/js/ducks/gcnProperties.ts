/**
 * GCN event properties (list of available property names for filtering).
 *
 * RTK Query conversion of the old `FETCH_GCN_PROPERTIES` duck. The endpoint is
 * injected into the central `skyportalApi`. The websocket refresh message
 * (`skyportal/FETCH_GCN_PROPERTIES`) is bridged to cache invalidation via
 * `invalidateOnMessage`; the old handler ignored the payload and always
 * refreshed, so we unconditionally invalidate the `GcnProperties` tag.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type GcnProperties = string[];

export interface FetchGcnPropertiesArgs {
  [key: string]: unknown;
}

export const gcnPropertiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnProperties: build.query<GcnProperties, FetchGcnPropertiesArgs | void>(
      {
        query: (filterParams) => {
          const params = new URLSearchParams(
            (filterParams as Record<string, string>) ?? {},
          ).toString();
          return `api/gcn_event/properties${params ? `?${params}` : ""}`;
        },
        providesTags: ["GcnProperties"],
      },
    ),
  }),
});

// Bridge the websocket refresh message to cache invalidation. The old handler
// always re-fetched on this actionType regardless of payload.
invalidateOnMessage("skyportal/FETCH_GCN_PROPERTIES", () => ["GcnProperties"]);

export const { useGetGcnPropertiesQuery } = gcnPropertiesApi;
