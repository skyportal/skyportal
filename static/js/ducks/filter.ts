import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

const filterApi = skyportalApi.injectEndpoints({
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
    addGroupFilter: build.mutation<
      { id: number },
      {
        name: string;
        group_id: number | string;
        stream_id: number | string;
        broker_id?: number | string | null;
      }
    >({
      query: (body) => ({ url: "api/filters", method: "POST", body }),
      invalidatesTags: (_result, _error, { group_id }) => [
        "Filters",
        "Broker",
        { type: "Group", id: Number(group_id) },
      ],
    }),
    deleteGroupFilter: build.mutation<unknown, { filter_id: number | string }>({
      query: ({ filter_id }) => ({
        url: `api/filters/${filter_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Filters", "Broker"],
    }),
    updateFilter: build.mutation<
      unknown,
      {
        filter_id: number | string;
        name?: string;
        altdata?: Record<string, any>;
      }
    >({
      query: ({ filter_id, ...body }) => ({
        url: `api/filters/${filter_id}`,
        method: "PATCH",
        body,
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
  useUpdateFilterMutation,
} = filterApi;
