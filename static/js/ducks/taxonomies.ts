/**
 * Classification taxonomies.
 *
 * RTK Query conversion of the old `FETCH_TAXONOMIES` duck, calling the typed
 * `skyportal-js` client. The websocket `REFRESH_TAXONOMIES` message invalidates
 * the taxonomy list; mutations submit, modify, and delete taxonomies.
 */
import type {
  Taxonomy,
  TaxonomyPost,
  TaxonomyPut,
} from "skyportal-js/Taxonomies";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface ModifyTaxonomyArg {
  id: number | string;
  params: TaxonomyPut;
}

export const taxonomiesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTaxonomies: build.query<Taxonomy[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchTaxonomies()),
      providesTags: ["Taxonomy"],
    }),
    submitTaxonomy: build.mutation<{ taxonomy_id: number }, TaxonomyPost>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.postTaxonomy(params)),
      invalidatesTags: ["Taxonomy"],
    }),
    modifyTaxonomy: build.mutation<void, ModifyTaxonomyArg>({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) => client.updateTaxonomy(Number(id), params)),
      invalidatesTags: ["Taxonomy"],
    }),
    deleteTaxonomy: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteTaxonomy(Number(id))),
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
