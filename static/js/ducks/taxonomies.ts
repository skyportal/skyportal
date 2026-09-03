/**
 * Classification taxonomies.
 *
 * RTK Query conversion of the old `FETCH_TAXONOMIES` duck. The websocket
 * `REFRESH_TAXONOMIES` message invalidates the taxonomy list; mutations
 * submit, modify, and delete taxonomies.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

interface ModifyTaxonomyArg {
  id: number | string;
  params: Record<string, any>;
}

export const taxonomiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTaxonomies: build.query<RouteData<"GET /api/taxonomy">, void>({
      query: () => "api/taxonomy",
      providesTags: ["Taxonomy"],
    }),
    submitTaxonomy: build.mutation<unknown, Record<string, any>>({
      query: (params) => ({
        url: "api/taxonomy",
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["Taxonomy"],
    }),
    modifyTaxonomy: build.mutation<unknown, ModifyTaxonomyArg>({
      query: ({ id, params }) => ({
        url: `api/taxonomy/${id}`,
        method: "PUT",
        body: params,
      }),
      invalidatesTags: ["Taxonomy"],
    }),
    deleteTaxonomy: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/taxonomy/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Taxonomy"],
    }),
  }),
});

// Websocket: the old handler refetched the full taxonomy list on
// REFRESH_TAXONOMIES.
invalidateOnMessage("skyportal/REFRESH_TAXONOMIES", () => ["Taxonomy"]);

export const {
  useGetTaxonomiesQuery,
  useSubmitTaxonomyMutation,
  useModifyTaxonomyMutation,
  useDeleteTaxonomyMutation,
} = taxonomiesApi;
