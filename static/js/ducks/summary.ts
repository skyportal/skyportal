/**
 * Summary similarity search.
 *
 * RTK Query conversion of the old `FETCH_MATCHING_SUMMARIES` duck. The backend
 * `POST /api/summary_query` runs a (semantically read-only) natural-language /
 * vector similarity search, so it is modelled as a mutation invoked imperatively
 * by consumers via `.unwrap()`. There is no websocket refresh for this duck.
 */
import type {
  SummaryQueryPost,
  SummaryQueryResults,
} from "skyportal-js/SummaryQuery";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

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
    fetchSummaryQuery: build.mutation<SummaryQueryResults, SummaryQueryPost>({
      queryFn: (formData, api) =>
        clientQuery(api, (client) => client.postSummaryQuery(formData)),
    }),
  }),
});

export const { useFetchSummaryQueryMutation } = summaryApi;
