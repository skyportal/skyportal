/**
 * Observing runs (the "observingRunList" listing).
 *
 * RTK Query conversion of the old `FETCH_OBSERVING_RUNS` duck, calling the typed
 * `skyportal-js` client. The backend returns the array of observing runs that
 * consumers used to read from `state.observingRuns.observingRunList`.
 *
 * The websocket `FETCH_OBSERVING_RUNS` message is bridged to cache invalidation
 * via `invalidateOnMessage`.
 */
import type { ObservingRun } from "skyportal-js/ObservingRuns";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const observingRunsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getObservingRuns: build.query<ObservingRun[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchObservingRuns()),
      providesTags: ["ObservingRun"],
    }),
  }),
});

// Websocket: old handler refetched observing runs on FETCH_OBSERVING_RUNS.
invalidateOnMessage("skyportal/FETCH_OBSERVING_RUNS", () => ["ObservingRun"]);

export const { useGetObservingRunsQuery } = observingRunsApi;
