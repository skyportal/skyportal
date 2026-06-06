/**
 * Single observing run (the run currently being viewed).
 *
 * RTK Query conversion of the old `FETCH_OBSERVING_RUN` duck. The endpoint is
 * injected into the central `skyportalApi`. `getObservingRun` fetches one run by
 * id; the create/modify/delete/not-observed actions are mutations that
 * invalidate the `ObservingRun` tag so the active run query refetches.
 *
 * The websocket `REFRESH_OBSERVING_RUN` message is bridged to cache
 * invalidation via `invalidateOnMessage`, preserving the old conditional
 * behaviour: only invalidate the run that was actually pushed (the per-id tag),
 * so an unrelated run's view does not refetch.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type ObservingRun = Record<string, any>;

export const observingRunApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getObservingRun: build.query<ObservingRun, number | string>({
      query: (id) => `api/observing_run/${id}`,
      providesTags: (_result, _error, id) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
    submitObservingRun: build.mutation<unknown, Record<string, any>>({
      query: (run) => ({
        url: "api/observing_run",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["ObservingRun"],
    }),
    modifyObservingRun: build.mutation<
      unknown,
      { id: number | string; run: Record<string, any> }
    >({
      query: ({ id, run }) => ({
        url: `api/observing_run/${id}`,
        method: "PUT",
        body: run,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
    deleteObservingRun: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/observing_run/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
    putObservingRunNotObserved: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/observing_run/${id}/not_observed`,
        method: "PUT",
        body: { current_status: "pending", new_status: "not observed" },
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
  }),
});

// Websocket: old handler refetched the run only when the pushed run_id matched
// the currently-loaded run. Invalidating the per-id tag achieves the same: only
// an active query for that run refetches.
invalidateOnMessage("skyportal/REFRESH_OBSERVING_RUN", (payload) =>
  payload?.run_id != null
    ? [{ type: "ObservingRun", id: payload.run_id }]
    : null,
);

export const {
  useGetObservingRunQuery,
  useSubmitObservingRunMutation,
  useModifyObservingRunMutation,
  useDeleteObservingRunMutation,
  usePutObservingRunNotObservedMutation,
} = observingRunApi;
