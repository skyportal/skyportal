/**
 * Single alert-stream filter (the `/filter/:id` page) plus group filter
 * add/delete.
 *
 * RTK Query conversion of the old `FETCH_FILTER` / `ADD_GROUP_FILTER` /
 * `DELETE_GROUP_FILTER` duck. The endpoints are injected into the central
 * `skyportalApi`. The queries provide the `Filters` tag; the add/delete
 * mutations invalidate it (to refresh the filter list/single) and consumers
 * still invalidate the owning *group* via `groupApi.util.invalidateTags`.
 */
import type { Filter } from "skyportal-js/Filters";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export interface AddGroupFilterArg {
  name: string;
  group_id: number | string;
  stream_id: number | string;
}

export interface DeleteGroupFilterArg {
  filter_id: number | string;
}

export interface UpdateFilterNameArg {
  filter_id: number | string;
  name: string;
}

export const filterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFilters: build.query<Filter[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchFilters()),
      providesTags: ["Filters"],
    }),
    getFilter: build.query<Filter, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchFilter(Number(id))),
      providesTags: ["Filters"],
    }),
    addGroupFilter: build.mutation<{ id: number }, AddGroupFilterArg>({
      queryFn: ({ name, group_id, stream_id }, api) =>
        clientQuery(api, (client) =>
          client.postFilter({
            name,
            group_id: Number(group_id),
            stream_id: Number(stream_id),
          }),
        ),
      // Also refresh any filter query (list/single); consumers still invalidate
      // the owning group separately.
      invalidatesTags: ["Filters"],
    }),
    deleteGroupFilter: build.mutation<void, DeleteGroupFilterArg>({
      queryFn: ({ filter_id }, api) =>
        clientQuery(api, (client) => client.deleteFilter(Number(filter_id))),
      invalidatesTags: ["Filters"],
    }),
    updateFilterName: build.mutation<void, UpdateFilterNameArg>({
      queryFn: ({ filter_id, name }, api) =>
        clientQuery(api, (client) =>
          client.updateFilter(Number(filter_id), { name }),
        ),
      invalidatesTags: ["Filters"],
    }),
  }),
});

export const {
  useGetFiltersQuery,
  useGetFilterQuery,
  useAddGroupFilterMutation,
  useDeleteGroupFilterMutation,
  useUpdateFilterNameMutation,
} = filterApi;
