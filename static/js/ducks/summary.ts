/**
 * Summary similarity search.
 *
 * RTK Query conversion of the old `FETCH_MATCHING_SUMMARIES` duck. The backend
 * `POST /api/summary_query` runs a (semantically read-only) natural-language /
 * vector similarity search, so it is modelled as a mutation invoked imperatively
 * by consumers via `.unwrap()`. There is no websocket refresh for this duck.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface SummaryQueryResultItem {
  id: string;
  score?: number | undefined;
  metadata?: Record<string, unknown> | undefined;
  [key: string]: unknown;
}

export interface SummaryQueryResult {
  query_results?: SummaryQueryResultItem[] | undefined;
  [key: string]: unknown;
}

export const summaryApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    fetchSummaryQuery: build.mutation<SummaryQueryResult, Record<string, any>>({
      query: (formData) => ({
        url: "api/summary_query",
        method: "POST",
        body: formData,
      }),
    }),
  }),
});

export const { useFetchSummaryQueryMutation } = summaryApi;
