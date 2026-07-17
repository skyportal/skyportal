import { skyportalApi } from "../api/skyportalApi";

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

// Run a BOOM filter (count-only or paginated "test"). Both legacy thunks
// (runBoomFilter / runBoomTestFilter) POSTed the same endpoint with different
// params, so they collapse to one mutation. The old "query_result" slice had no
// reader (the result was used inline from the await), and clearBoomFilter maps
// to the mutation hook's reset().
export const boomRunFilterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    runBoomFilter: build.mutation<any, RunBoomFilterArg>({
      query: (body) => ({
        url: "api/boom/run_filter",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useRunBoomFilterMutation } = boomRunFilterApi;
