/**
 * Sources confirmed/rejected within a GCN event ("sources in GCN").
 *
 * RTK Query conversion of the old `FETCH_SOURCES_IN_GCN` duck. The list is keyed
 * by GCN `dateobs` plus the localization/source filter; mutations
 * submit/patch/delete the confirmation status of a single source and invalidate
 * the `SourceInGcn` tag so the list refetches.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface SourceInGcn {
  obj_id: string;
  confirmed?: boolean | null;
  explanation?: string | undefined;
  notes?: string | undefined;
  [key: string]: unknown;
}

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
    getSourcesInGcn: build.query<SourceInGcn[], FetchSourcesInGcnArg>({
      query: ({ dateobs, ...filterParams }) => {
        const cleaned: Record<string, string> = {};
        Object.entries(filterParams).forEach(([key, value]) => {
          if (value === undefined || value === null) {
            return;
          }
          if (Array.isArray(value)) {
            if (value.length > 0) {
              cleaned[key] = value.join(",");
            }
          } else {
            cleaned[key] = String(value);
          }
        });
        const params = new URLSearchParams(cleaned).toString();
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
    patchSourceInGcn: build.mutation<unknown, PatchSourceInGcnArg>({
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
