/**
 * Sources confirmed/rejected within a GCN event ("sources in GCN").
 *
 * RTK Query conversion of the old `FETCH_SOURCES_IN_GCN` duck. The list is keyed
 * by GCN `dateobs` plus the localization/source filter; mutations
 * submit/patch/delete the confirmation status of a single source and invalidate
 * the `SourceInGcn` tag so the list refetches.
 */
import type {
  GcnEventObj,
  GcnEventObjPost,
  GcnEventObjStatus,
} from "skyportal-js/GcnEvents";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

interface FetchSourcesInGcnArg {
  dateobs: string;
  /**
   * Only used as part of the cache key: the handler reads `sourcesIDList` and
   * nothing else.
   */
  localizationName?: string | undefined;
  sourcesIdList?: (string | number)[] | undefined;
}

interface SubmitSourceInGcnArg {
  dateobs: string;
  data: GcnEventObjPost;
}

interface PatchSourceInGcnArg {
  dateobs: string;
  source_id: number | string;
  data: { status: GcnEventObjStatus; explanation?: string; notes?: string };
}

interface DeleteSourceInGcnArg {
  dateobs: string;
  source_id: number | string;
}

export const sourcesInGcnApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSourcesInGcn: build.query<GcnEventObj[], FetchSourcesInGcnArg>({
      queryFn: ({ dateobs, sourcesIdList }, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEventSources(dateobs, {
            sourceIds: sourcesIdList?.map(String),
          }),
        ),
      providesTags: ["SourceInGcn"],
    }),
    submitSourceInGcn: build.mutation<{ id: number }, SubmitSourceInGcnArg>({
      queryFn: ({ dateobs, data }, api) =>
        clientQuery(api, (client) => client.postGcnEventSource(dateobs, data)),
      invalidatesTags: ["SourceInGcn"],
    }),
    patchSourceInGcn: build.mutation<{ id: number }, PatchSourceInGcnArg>({
      queryFn: ({ dateobs, source_id, data }, api) =>
        clientQuery(api, (client) =>
          client.updateGcnEventSource(dateobs, String(source_id), data.status, {
            explanation: data.explanation,
            notes: data.notes,
          }),
        ),
      invalidatesTags: ["SourceInGcn"],
    }),
    deleteSourceInGcn: build.mutation<{ id: number }, DeleteSourceInGcnArg>({
      queryFn: ({ dateobs, source_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteGcnEventSource(dateobs, String(source_id)),
        ),
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
