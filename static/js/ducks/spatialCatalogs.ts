/**
 * Spatial catalogs.
 *
 * RTK Query conversion of the old `FETCH_SPATIAL_CATALOGS` /
 * `FETCH_SPATIAL_CATALOG` ducks. The list query is injected into the central
 * `skyportalApi`; the single-catalog query fetches one catalog by id. Upload and
 * delete are mutations that invalidate the relevant tags so the list/detail
 * refetch.
 *
 * Websocket-driven invalidation bridges `REFRESH_SPATIAL_CATALOGS` (refetch the
 * full list) and `REFRESH_SPATIAL_CATALOG` (refetch a single catalog, but only
 * when the pushed id matches a catalog that is currently cached) to cache
 * invalidation.
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export const spatialCatalogsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSpatialCatalogs: build.query<
      RouteData<"GET /api/spatial_catalog">,
      Record<string, unknown> | void
    >({
      query: (filterParams) => {
        const params = buildQueryString(filterParams ?? {});
        return params ? `api/spatial_catalog?${params}` : "api/spatial_catalog";
      },
      providesTags: ["SpatialCatalogs"],
    }),
    getSpatialCatalog: build.query<
      RouteData<"GET /api/spatial_catalog/{catalog_id}">,
      number | string
    >({
      query: (id) => `api/spatial_catalog/${id}`,
      providesTags: ["SpatialCatalog"],
    }),
    uploadSpatialCatalogs: build.mutation<unknown, Record<string, unknown>>({
      query: (data) => ({
        url: "api/spatial_catalog/ascii",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["SpatialCatalogs"],
    }),
    deleteSpatialCatalog: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/spatial_catalog/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["SpatialCatalogs", "SpatialCatalog"],
    }),
  }),
});

// Websocket: refresh the full list on REFRESH_SPATIAL_CATALOGS.
invalidateOnMessage("skyportal/REFRESH_SPATIAL_CATALOGS", () => [
  "SpatialCatalogs",
]);

// Websocket: refresh a single catalog on REFRESH_SPATIAL_CATALOG, but only when
// the pushed id matches a catalog currently held in the cache (preserving the
// old handler's "only refresh if the loaded catalog matches" gating).
invalidateOnMessage(
  "skyportal/REFRESH_SPATIAL_CATALOG",
  (payload, getState) => {
    const selectCatalog = spatialCatalogsApi.endpoints.getSpatialCatalog.select(
      payload?.spatialCatalog_id,
    );
    const state = getState() as Parameters<typeof selectCatalog>[0];
    const cached = selectCatalog(state)?.data;
    return cached ? ["SpatialCatalog"] : null;
  },
);

export const {
  useGetSpatialCatalogsQuery,
  useGetSpatialCatalogQuery,
  useUploadSpatialCatalogsMutation,
  useDeleteSpatialCatalogMutation,
} = spatialCatalogsApi;
