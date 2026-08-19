/**
 * Catalog queries.
 *
 * RTK Query conversion of the old `FETCH_CATALOG_QUERIES` / `SUBMIT_CATALOG_QUERY`
 * duck. `getCatalogQueries` lists the queries; `submitCatalogQuery` posts a new
 * one and invalidates the `CatalogQuery` tag so the list refetches.
 *
 * The websocket `REFRESH_CATALOG_QUERIES` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import type { CatalogQueryPost } from "skyportal-js/CatalogQueries";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type CatalogQuery = Record<string, any>;

export const catalogQueryApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // raw, and unused: CatalogQueryHandler implements only post(), so this GET
    // is answered with 405.
    getCatalogQueries: build.query<CatalogQuery[], void>({
      query: () => "api/catalog_queries",
      providesTags: ["CatalogQuery"],
    }),
    submitCatalogQuery: build.mutation<void, CatalogQueryPost>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.postCatalogQuery(data)),
      invalidatesTags: ["CatalogQuery"],
    }),
  }),
});

// Websocket: old handler refetched catalog queries on REFRESH_CATALOG_QUERIES.
invalidateOnMessage("skyportal/REFRESH_CATALOG_QUERIES", () => [
  "CatalogQuery",
]);

export const { useGetCatalogQueriesQuery, useSubmitCatalogQueryMutation } =
  catalogQueryApi;
