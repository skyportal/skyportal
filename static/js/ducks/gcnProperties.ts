/**
 * GCN event properties (list of available property names for filtering).
 *
 * RTK Query conversion of the old `FETCH_GCN_PROPERTIES` duck. The endpoint is
 * injected into the central `skyportalApi`.
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

export interface FetchGcnPropertiesArgs {
  [key: string]: unknown;
}

export const gcnPropertiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnProperties: build.query<
      RouteData<"GET /api/gcn_event/properties">,
      FetchGcnPropertiesArgs | void
    >({
      query: (filterParams) => {
        const params = buildQueryString(
          (filterParams as Record<string, string>) ?? {},
        );
        return `api/gcn_event/properties${params ? `?${params}` : ""}`;
      },
      providesTags: ["GcnProperties"],
    }),
  }),
});

export const { useGetGcnPropertiesQuery } = gcnPropertiesApi;
