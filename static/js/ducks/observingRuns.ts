/**
 * Observing runs (the "observingRunList" listing).
 *
 * RTK Query conversion of the old `FETCH_OBSERVING_RUNS` duck. The endpoint is
 * injected into the central `skyportalApi`. The backend returns the array of
 * observing runs that consumers used to read from `state.observingRuns
 * .observingRunList`.
 *
 * The websocket `FETCH_OBSERVING_RUNS` message is bridged to cache invalidation
 * via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type ObservingRun = Record<string, any>;

export const observingRunsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getObservingRuns: build.query<ObservingRun[], void>({
      query: () => "api/observing_run",
      providesTags: ["ObservingRun"],
    }),
  }),
});

// Websocket: old handler refetched observing runs on FETCH_OBSERVING_RUNS.
invalidateOnMessage("skyportal/FETCH_OBSERVING_RUNS", () => ["ObservingRun"]);

export const { useGetObservingRunsQuery } = observingRunsApi;
