/**
 * Sources confirmed/rejected within a GCN event ("sources in GCN").
 *
 * RTK Query conversion of the old `FETCH_SOURCES_IN_GCN` duck. The list is keyed
 * by GCN `dateobs` plus the localization/source filter; mutations
 * submit/patch/delete the confirmation status of a single source and invalidate
 * the `SourceInGcn` tag so the list refetches.
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

interface FetchSourcesInGcnArg {
  dateobs: string;
  localizationName?: string | undefined;
  sourcesIdList?: (string | number)[] | undefined;
}

interface SubmitSourceInGcnArg {
  dateobs: string;
  data: Record<string, unknown>;
}

interface PatchSourceInGcnArg {
  dateobs: string;
  source_id: number | string;
  data: Record<string, unknown>;
}

interface DeleteSourceInGcnArg {
  dateobs: string;
  source_id: number | string;
}

export const sourcesInGcnApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSourcesInGcn: build.query<
      RouteData<"GET /api/sources_in_gcn/{dateobs}">,
      FetchSourcesInGcnArg
    >({
      query: ({ dateobs, ...filterParams }) => {
        const params = buildQueryString(filterParams);
        return params
          ? `api/sources_in_gcn/${dateobs}?${params}`
          : `api/sources_in_gcn/${dateobs}`;
      },
      providesTags: ["SourceInGcn"],
    }),
    submitSourceInGcn: build.mutation<unknown, SubmitSourceInGcnArg>({
      query: ({ dateobs, data }) => ({
        url: `api/sources_in_gcn/${dateobs}`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["SourceInGcn"],
    }),
    patchSourceInGcn: build.mutation<
      RouteData<"PATCH /api/sources_in_gcn/{dateobs}/{source_id}">,
      PatchSourceInGcnArg
    >({
      query: ({ dateobs, source_id, data }) => ({
        url: `api/sources_in_gcn/${dateobs}/${source_id}`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["SourceInGcn"],
    }),
    deleteSourceInGcn: build.mutation<unknown, DeleteSourceInGcnArg>({
      query: ({ dateobs, source_id }) => ({
        url: `api/sources_in_gcn/${dateobs}/${source_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["SourceInGcn"],
    }),
  }),
});

export const {
  useGetSourcesInGcnQuery,
  useLazyGetSourcesInGcnQuery,
  useSubmitSourceInGcnMutation,
  usePatchSourceInGcnMutation,
  useDeleteSourceInGcnMutation,
} = sourcesInGcnApi;
