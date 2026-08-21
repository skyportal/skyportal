/**
 * Earthquake statuses (list of available status tags).
 *
 * RTK Query conversion of the old `FETCH_EARTHQUAKE_STATUSES` duck, calling the
 * typed `skyportal-js` client.
 *
 * The old websocket handler re-fetched the statuses whenever a
 * `FETCH_EARTHQUAKE_STATUSES` message arrived, unconditionally. The RTK Query
 * equivalent invalidates the `EarthquakeStatus` tag so any active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type EarthquakeStatuses = string[];

export const earthquakeStatusesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed filter params
    // that the server ignored.
    getEarthquakeStatuses: build.query<EarthquakeStatuses, void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchEarthquakeStatuses()),
      providesTags: ["EarthquakeStatus"],
    }),
  }),
});

export const { useGetEarthquakeStatusesQuery } = earthquakeStatusesApi;

// Websocket message handler: refresh the statuses list on any push.
invalidateOnMessage("skyportal/FETCH_EARTHQUAKE_STATUSES", () => [
  "EarthquakeStatus",
]);
