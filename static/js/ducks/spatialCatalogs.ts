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
import type { SpatialCatalog } from "skyportal-js/SpatialCatalogs";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const spatialCatalogsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler's only query param (catalog_name) is read but never applied,
    // so the old duck's filter params had no effect.
    getSpatialCatalogs: build.query<SpatialCatalog[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchSpatialCatalogs()),
      providesTags: ["SpatialCatalogs"],
    }),
    getSpatialCatalog: build.query<SpatialCatalog, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchSpatialCatalog(Number(id))),
      providesTags: ["SpatialCatalog"],
    }),
    uploadSpatialCatalogs: build.mutation<
      { id: number },
      { catalogName: string; catalogData: string }
    >({
      queryFn: ({ catalogName, catalogData }, api) =>
        clientQuery(api, (client) =>
          client.postSpatialCatalogAscii(catalogName, catalogData),
        ),
      invalidatesTags: ["SpatialCatalogs"],
    }),
    deleteSpatialCatalog: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteSpatialCatalog(Number(id))),
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
