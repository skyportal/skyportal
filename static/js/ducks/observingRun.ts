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
import type {
  ObservingRun,
  ObservingRunPost,
  ObservingRunUpdate,
} from "skyportal-js/ObservingRuns";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const observingRunApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getObservingRun: build.query<ObservingRun, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchObservingRun(Number(id))),
      providesTags: (_result, _error, id) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
    submitObservingRun: build.mutation<{ id: number }, ObservingRunPost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postObservingRun(run)),
      invalidatesTags: ["ObservingRun"],
    }),
    modifyObservingRun: build.mutation<
      void,
      { id: number | string; run: ObservingRunUpdate }
    >({
      queryFn: ({ id, run }, api) =>
        clientQuery(api, (client) =>
          client.updateObservingRun(Number(id), run),
        ),
      invalidatesTags: (_result, _error, { id }) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
    deleteObservingRun: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteObservingRun(Number(id))),
      invalidatesTags: (_result, _error, id) => [
        { type: "ObservingRun", id },
        "ObservingRun",
      ],
    }),
    putObservingRunNotObserved: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.updateObservingRunNotObserved(
            Number(id),
            "pending",
            "not observed",
          ),
        ),
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
