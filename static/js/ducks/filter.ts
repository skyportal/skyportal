/**
 * Single alert-stream filter (the `/filter/:id` page) plus group filter
 * add/delete.
 *
 * RTK Query conversion of the old `FETCH_FILTER` / `ADD_GROUP_FILTER` /
 * `DELETE_GROUP_FILTER` duck. The endpoints are injected into the central
 * `skyportalApi`. The query provides the `Filters` tag; the add/delete
 * mutations refresh the owning *group* (via the consumer's manual
 * `groupApi.util.invalidateTags`), so they carry no `invalidatesTags` here.
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

export const filterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
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
    }),
    deleteGroupFilter: build.mutation<unknown, DeleteGroupFilterArg>({
      query: ({ filter_id }) => ({
        url: `api/filters/${filter_id}`,
        method: "DELETE",
      }),
    }),
  }),
});

export const {
  useGetFilterQuery,
  useAddGroupFilterMutation,
  useDeleteGroupFilterMutation,
} = filterApi;
