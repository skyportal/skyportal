/**
 * Broker filter "test run" duck: preview which alerts a draft pipeline passes.
 *
 * RTK Query conversion of the old `boom_run_filter` action/reducer duck. The old
 * `runBoomFilter` / `runBoomTestFilter` thunks POSTed the same endpoint with
 * different params, so they collapse to one mutation; the old `query_result`
 * slice had no reader (the result was used inline from the await) and
 * `clearBoomFilter` maps to the mutation hook's `reset()`. Targets the active
 * broker via `brokerFilterBase()` (`/api/brokers/{id}/filter/test`).
 */
import { skyportalApi } from "../api/skyportalApi";
import { brokerFilterBase } from "./brokerFilterTarget";

export interface RunBoomFilterArg {
  pipeline: any;
  selectedCollection: any;
  start_jd: any;
  end_jd: any;
  filter_id: any;
  // present only for the paginated "test" variant
  sort_by?: any;
  sort_order?: any;
  limit?: any;
  cursor?: any;
}

export const boomRunFilterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    runBoomFilter: build.mutation<any, RunBoomFilterArg>({
      query: (body) => ({
        url: `${brokerFilterBase()}/filter/test`,
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useRunBoomFilterMutation } = boomRunFilterApi;
