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
import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

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
    getFilters: build.query<RouteData<"GET /api/filters">, void>({
      query: () => "api/filters",
      providesTags: ["Filters"],
    }),
    getFilter: build.query<
      RouteData<"GET /api/filters/{filter_id}">,
      number | string
    >({
      query: (id) => `api/filters/${id}`,
      providesTags: ["Filters"],
    }),
    addGroupFilter: build.mutation<unknown, AddGroupFilterArg>({
      query: ({ name, group_id, stream_id }) => ({
        url: "api/filters",
        method: "POST",
        body: { name, group_id, stream_id },
      }),
      // Also refresh any filter query (list/single); consumers still invalidate
      // the owning group separately.
      invalidatesTags: ["Filters"],
    }),
    deleteGroupFilter: build.mutation<unknown, DeleteGroupFilterArg>({
      query: ({ filter_id }) => ({
        url: `api/filters/${filter_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Filters"],
    }),
    updateFilterName: build.mutation<unknown, UpdateFilterNameArg>({
      query: ({ filter_id, name }) => ({
        url: `api/filters/${filter_id}`,
        method: "PATCH",
        body: { name },
      }),
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
