/**
 * Earthquake statuses (list of available status tags).
 *
 * RTK Query conversion of the old `FETCH_EARTHQUAKE_STATUSES` duck. The endpoint
 * is injected into the central `skyportalApi`, so caching, loading and error
 * state are handled by RTK Query instead of a hand-written reducer.
 *
 * The old websocket handler re-fetched the statuses whenever a
 * `FETCH_EARTHQUAKE_STATUSES` message arrived, unconditionally. The RTK Query
 * equivalent invalidates the `EarthquakeStatus` tag so any active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type EarthquakeStatuses = string[];

export interface EarthquakeStatusesArg {
  [key: string]: unknown;
}

export const earthquakeStatusesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getEarthquakeStatuses: build.query<
      EarthquakeStatuses,
      EarthquakeStatusesArg | void
    >({
      query: (filterParams) => {
        const params = new URLSearchParams(
          (filterParams as Record<string, string>) ?? {},
        ).toString();
        return params
          ? `api/earthquake/status?${params}`
          : "api/earthquake/status";
      },
      providesTags: ["EarthquakeStatus"],
    }),
  }),
});

export const { useGetEarthquakeStatusesQuery } = earthquakeStatusesApi;

// Websocket message handler: refresh the statuses list on any push.
invalidateOnMessage("skyportal/FETCH_EARTHQUAKE_STATUSES", () => [
  "EarthquakeStatus",
]);
