/**
 * Source (the single loaded source detail + all its sub-resources and the many
 * mutations that act on a source).
 *
 * RTK Query conversion of the old composite `source` duck. The old reducer
 * built ONE `source` slice out of many independent sub-fetches (the main source
 * object via `fetchSource`, the adjusted position, the associated GCNs, the
 * analyses list, and a comment attachment), and registered ~40 thunks that
 * POST/PATCH/PUT/DELETE against the source. Here each read becomes its own
 * `build.query`, keyed by its own argument and cached independently, and every
 * write becomes its own `build.mutation`.
 *
 * Consumers that used to read `state.source.<subfield>` now call the matching
 * query hook. Queries that surface source data provide the `Source` tag;
 * mutations that change source data invalidate it. The websocket `REFRESH_*`
 * messages are bridged to cache invalidation via `invalidateOnMessage`, so only
 * the active (currently-loaded) source's queries refetch.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage, findCachedQueryArg } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";
import { sourceTag } from "./sourceTags";

export const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";
export const REFRESH_SOURCE_POSITION = "skyportal/REFRESH_SOURCE_POSITION";
export const REFRESH_OBJ_ANALYSES = "skyportal/REFRESH_OBJ_ANALYSES";

export interface SourcePosition {
  ra?: number | undefined;
  dec?: number | undefined;
  gal_lon?: number | undefined;
  gal_lat?: number | undefined;
  ebv?: number | undefined;
  separation?: number | undefined;
  [key: string]: any;
}

export interface AssociatedGcns {
  gcns?: string[] | undefined;
  [key: string]: any;
}

export interface CommentAttachment {
  commentId: number | string;
  text: string;
  attachment: string;
  attachment_name: string;
  [key: string]: any;
}

function fileReaderPromise(
  file: File,
): Promise<{ body: string | ArrayBuffer | null; name: string }> {
  return new Promise((resolve) => {
    const filereader = new FileReader();
    filereader.readAsDataURL(file);
    filereader.onloadend = () =>
      resolve({ body: filereader.result, name: file.name });
  });
}

// The big include-flags query string used by `getSource`. Preserved verbatim
// from the old `fetchSource` thunk.
const sourceIncludeParams = {
  includeComments: true,
  includeColorMagnitude: true,
  includeThumbnails: true,
  includePhotometryExists: true,
  includeSpectrumExists: true,
  includeLabellers: true,
  includeDetectionStats: true,
  includeGCNCrossmatches: true,
  includeGCNNotes: true,
  includeCandidates: true,
  // Aggregate classifications across meta-object (SuperObj) members, with
  // per-source provenance. No-ops for non-meta sources (mirrors the
  // includeSuperObjsPhotometry flag on the photometry endpoint).
  includeSuperObjs: true,
};

export const sourceApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // ----- Main source + read-only sub-fetches -----
    getSource: build.query<
      RouteData<"GET /api/sources/{obj_id}">,
      number | string
    >({
      query: (id) => {
        const queryString = new URLSearchParams(
          sourceIncludeParams as unknown as Record<string, string>,
        ).toString();
        return `api/sources/${id}?${queryString}`;
      },
      // Provides both the broad "Source" tag (so the existing mutations, which
      // invalidate ["Source"], keep refetching) and a per-id tag so a websocket
      // REFRESH for one source invalidates only that source's cache entry.
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    // Lightweight: the groups an obj is currently saved/requested to (empty for an
    // unsaved candidate). Used to seed the toolbar save-to-groups dialog.
    getObjGroups: build.query<any[], number | string>({
      query: (id) => `api/sources/${id}/groups`,
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    getSourcePosition: build.query<SourcePosition, number | string>({
      query: (id) => `api/sources/${id}/position`,
      // Position has its own REFRESH_SOURCE_POSITION event, so it gets its own
      // per-id tag (a REFRESH_SOURCE from e.g. a comment must NOT refetch it).
      // The broad "Source" tag is kept so source mutations still refetch it.
      providesTags: (_result, _error, id) => [
        "Source",
        { type: "Source", id },
        { type: "SourcePosition", id },
      ],
    }),
    getAssociatedGcns: build.query<AssociatedGcns, number | string>({
      query: (id) => `api/associated_gcns/${id}`,
      // Broad "Source" (so any broad source mutation still refetches it) plus a
      // per-id tag so per-source mutations (e.g. addGCNCrossmatch) refresh only
      // this source's associated GCNs.
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    getAnalyses: build.query<
      RouteData<"GET /api/{analysis_resource_type}/analysis">,
      {
        analysis_resource_type?: string | undefined;
        params?: Record<string, any> | undefined;
      }
    >({
      query: ({ analysis_resource_type = "obj", params = {} }) => ({
        url: `api/${analysis_resource_type}/analysis`,
        params,
      }),
      providesTags: ["Source"],
    }),
    getAnalysis: build.query<
      RouteData<"GET /api/{analysis_resource_type}/analysis/{analysis_id}">,
      {
        analysis_id: number | string;
        analysis_resource_type?: string | undefined;
        params?: Record<string, any> | undefined;
      }
    >({
      query: ({
        analysis_id,
        analysis_resource_type = "obj",
        params = {},
      }) => ({
        url: `api/${analysis_resource_type}/analysis/${analysis_id}`,
        params,
      }),
    }),
    getAnalysisResults: build.query<
      any,
      {
        analysis_id: number | string;
        analysis_resource_type?: string | undefined;
        params?: Record<string, any> | undefined;
      }
    >({
      query: ({
        analysis_id,
        analysis_resource_type = "obj",
        params = {},
      }) => ({
        url: `api/${analysis_resource_type}/analysis/${analysis_id}/results`,
        params,
      }),
    }),
    // An imperative one-off existence check (used in submit handlers via
    // `await checkSource(...).unwrap()`), so it's a mutation, not a lazy query:
    // a lazy-query trigger's `.unwrap()` in a handler can reject on subscription
    // teardown, which the callers' empty `catch` swallows — silently aborting
    // the subsequent saveSource.
    checkSource: build.mutation<
      any,
      { id: number | string; params: Record<string, any> }
    >({
      query: ({ id, params }) => {
        const queryParams = params["nameOnly"]
          ? ""
          : `?ra=${params["ra"]}&dec=${params["dec"]}&radius=0.0003`;
        return {
          url: `api/source_exists/${id}${queryParams}`,
          method: "GET",
        };
      },
    }),
    getPhotometryRequest: build.query<
      any,
      { id: number | string; params?: Record<string, any> | undefined }
    >({
      query: ({ id, params = {} }) => ({
        url: `api/photometry_request/${id}`,
        params,
      }),
    }),
    getSourceFinderChart: build.query<
      any,
      { id: number | string; params: Record<string, any> }
    >({
      query: ({ id, params }) => ({
        url: `api/sources/${id}/finder`,
        params,
      }),
    }),
    getCommentTextAttachment: build.query<
      CommentAttachment,
      { sourceID: number | string; commentID: number | string }
    >({
      query: ({ sourceID, commentID }) =>
        `api/sources/${sourceID}/comments/${commentID}/attachment?download=false&preview=false`,
    }),
    getCommentOnSpectrumTextAttachment: build.query<
      CommentAttachment,
      { spectrumID: number | string; commentID: number | string }
    >({
      query: ({ spectrumID, commentID }) =>
        `api/spectra/${spectrumID}/comments/${commentID}/attachment?download=false&preview=false`,
    }),

    // ----- Save / update / transfer -----
    saveSource: build.mutation<any, Record<string, any>>({
      query: (payload) => ({
        url: "api/sources",
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["Source"],
    }),
    updateSource: build.mutation<
      RouteData<"PATCH /api/sources/{obj_id}">,
      { id: number | string; payload: Record<string, any> }
    >({
      query: ({ id, payload }) => ({
        url: `api/sources/${id}`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    updateSourceGroups: build.mutation<any, Record<string, any>>({
      query: (payload) => ({
        url: "api/source_groups",
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["Source"],
    }),
    acceptSaveRequest: build.mutation<
      any,
      { sourceID: number | string; groupID: number | string }
    >({
      query: ({ sourceID, groupID }) => ({
        url: `api/source_groups/${sourceID}`,
        method: "PATCH",
        body: { groupID, active: true, requested: false },
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    declineSaveRequest: build.mutation<
      any,
      { sourceID: number | string; groupID: number | string }
    >({
      query: ({ sourceID, groupID }) => ({
        url: `api/source_groups/${sourceID}`,
        method: "PATCH",
        body: { groupID, active: false, requested: false },
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    addSourceView: build.mutation<any, number | string>({
      query: (id) => ({
        url: `api/internal/source_views/${id}`,
        method: "POST",
      }),
    }),

    // ----- Classifications -----
    addClassification: build.mutation<any, Record<string, any>>({
      query: (formData) => ({
        url: "api/classification",
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, formData) =>
        sourceTag(formData?.["obj_id"]),
    }),
    deleteClassification: build.mutation<any, number | string>({
      query: (classificationID) => ({
        url: `api/classification/${classificationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Source"],
    }),
    deleteClassifications: build.mutation<any, number | string>({
      query: (sourceID) => ({
        url: `api/sources/${sourceID}/classifications`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    addClassificationVote: build.mutation<
      any,
      {
        classification_id: number | string;
        data?: Record<string, any> | undefined;
      }
    >({
      query: ({ classification_id, data = {} }) => ({
        url: `api/classification/votes/${classification_id}`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Source"],
    }),

    // ----- Comments -----
    addComment: build.mutation<
      RouteData<"POST /api/{associated_resource_type}/{resource_id}/comments">,
      Record<string, any>
    >({
      queryFn: async (formData, _api, _extra, baseQuery) => {
        const body = { ...formData };
        if (body["attachment"]) {
          body["attachment"] = await fileReaderPromise(body["attachment"]);
        }
        const url = body["spectrum_id"]
          ? `api/spectra/${body["spectrum_id"]}/comments`
          : `api/sources/${body["obj_id"]}/comments`;
        const result = await baseQuery({ url, method: "POST", body });
        if (result.error) {
          return { error: result.error };
        }
        return {
          data: result.data as RouteData<"POST /api/{associated_resource_type}/{resource_id}/comments">,
        };
      },
      invalidatesTags: (_result, _error, formData) =>
        sourceTag(formData?.["obj_id"]),
    }),
    editComment: build.mutation<
      RouteData<"PUT /api/{associated_resource_type}/{resource_id}/comments/{comment_id}">,
      { commentID: number | string; formData: Record<string, any> }
    >({
      queryFn: async ({ commentID, formData }, _api, _extra, baseQuery) => {
        const body = { ...formData };
        if (body["attachment"]) {
          body["attachment"] = await fileReaderPromise(body["attachment"]);
        }
        const url = body["spectrum_id"]
          ? `api/spectra/${body["spectrum_id"]}/comments/${commentID}`
          : `api/sources/${body["obj_id"]}/comments/${commentID}`;
        const result = await baseQuery({ url, method: "PUT", body });
        if (result.error) {
          return { error: result.error };
        }
        return {
          data: result.data as RouteData<"PUT /api/{associated_resource_type}/{resource_id}/comments/{comment_id}">,
        };
      },
      invalidatesTags: (_result, _error, { formData }) =>
        sourceTag(formData?.["obj_id"]),
    }),
    deleteComment: build.mutation<
      any,
      { sourceID: number | string; commentID: number | string }
    >({
      query: ({ sourceID, commentID }) => ({
        url: `api/sources/${sourceID}/comments/${commentID}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    deleteCommentOnSpectrum: build.mutation<
      any,
      { spectrumID: number | string; commentID: number | string }
    >({
      query: ({ spectrumID, commentID }) => ({
        url: `api/spectra/${spectrumID}/comments/${commentID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Source"],
    }),

    // ----- Annotations -----
    addAnnotation: build.mutation<
      any,
      { sourceID: number | string; formData: Record<string, any> }
    >({
      query: ({ sourceID, formData }) => ({
        url: `api/sources/${sourceID}/annotations`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    deleteAnnotation: build.mutation<
      any,
      { sourceID: number | string; annotationID: number | string }
    >({
      query: ({ sourceID, annotationID }) => ({
        url: `api/sources/${sourceID}/annotations/${annotationID}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),

    // ----- Labels -----
    addSourceLabels: build.mutation<
      any,
      { id: number | string; data: Record<string, any> }
    >({
      query: ({ id, data }) => ({
        url: `api/sources/${id}/labels`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    deleteSourceLabels: build.mutation<
      any,
      { id: number | string; data: Record<string, any> }
    >({
      query: ({ id, data }) => ({
        url: `api/sources/${id}/labels`,
        method: "DELETE",
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),

    // ----- Follow-up requests -----
    submitFollowupRequest: build.mutation<
      RouteData<"POST /api/followup_request">,
      Record<string, any>
    >({
      query: (params) => {
        const { instrument_name, ...paramsToSubmit } = params;
        return {
          url: "api/followup_request",
          method: "POST",
          body: paramsToSubmit,
        };
      },
      invalidatesTags: ["Source"],
    }),
    editFollowupRequest: build.mutation<
      RouteData<"PUT /api/followup_request/{request_id}">,
      { params: Record<string, any>; requestID: number | string }
    >({
      query: ({ params, requestID }) => {
        const { instrument_name, ...paramsToSubmit } = params;
        return {
          url: `api/followup_request/${requestID}`,
          method: "PUT",
          body: paramsToSubmit,
        };
      },
      invalidatesTags: ["Source"],
    }),
    deleteFollowupRequest: build.mutation<
      any,
      { id: number | string; params?: Record<string, any> | undefined }
    >({
      query: ({ id, params = {} }) => ({
        url: `api/followup_request/${id}`,
        method: "DELETE",
        body: params,
      }),
      invalidatesTags: ["Source"],
    }),

    // ----- Assignments -----
    submitAssignment: build.mutation<any, Record<string, any>>({
      query: (params) => ({
        url: "api/assignment",
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["Source"],
    }),
    editAssignment: build.mutation<
      any,
      { params: Record<string, any>; assignmentID: number | string }
    >({
      query: ({ params, assignmentID }) => ({
        url: `api/assignment/${assignmentID}`,
        method: "PUT",
        body: params,
      }),
      invalidatesTags: ["Source"],
    }),
    deleteAssignment: build.mutation<any, number | string>({
      query: (id) => ({
        url: `api/assignment/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Source"],
    }),

    // ----- Notifications / sharing / photometry -----
    sendAlert: build.mutation<
      RouteData<"POST /api/source_notifications">,
      Record<string, any>
    >({
      query: (params) => ({
        url: "api/source_notifications",
        method: "POST",
        body: params,
      }),
    }),
    shareData: build.mutation<any, Record<string, any>>({
      query: (data) => ({
        url: "api/sharing",
        method: "POST",
        body: data,
      }),
    }),
    uploadPhotometry: build.mutation<any, Record<string, any>>({
      query: (data) => ({
        url: "api/photometry?refresh=true",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Source"],
    }),
    copySourcePhotometry: build.mutation<
      any,
      { id: number | string; formData?: Record<string, any> | undefined }
    >({
      query: ({ id, formData = {} }) => ({
        url: `api/sources/${id}/copy_photometry`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),

    // ----- External-catalog annotations -----
    fetchGaia: build.mutation<
      RouteData<"POST /api/sources/{obj_id}/annotations/gaia">,
      number | string
    >({
      query: (sourceID) => ({
        url: `api/sources/${sourceID}/annotations/gaia`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    fetchWise: build.mutation<
      RouteData<"POST /api/sources/{obj_id}/annotations/irsa">,
      number | string
    >({
      query: (sourceID) => ({
        url: `api/sources/${sourceID}/annotations/irsa`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    fetchVizier: build.mutation<
      RouteData<"POST /api/sources/{obj_id}/annotations/vizier">,
      { sourceID: number | string; catalog?: string | undefined }
    >({
      query: ({ sourceID, catalog = "VII/290" }) => ({
        url: `api/sources/${sourceID}/annotations/vizier`,
        method: "POST",
        body: { catalog },
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    fetchPhotoz: build.mutation<any, number | string>({
      query: (sourceID) => ({
        url: `api/sources/${sourceID}/annotations/datalab`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    fetchPS1: build.mutation<
      RouteData<"POST /api/sources/{obj_id}/annotations/ps1">,
      number | string
    >({
      query: (sourceID) => ({
        url: `api/sources/${sourceID}/annotations/ps1`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),

    // ----- TNS / host / MPC / GCN crossmatch -----
    addTNS: build.mutation<
      any,
      { id: number | string; formData: Record<string, any> }
    >({
      query: ({ id, formData }) => ({
        url: `api/sources/${id}/tns`,
        params: formData,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    addHost: build.mutation<
      any,
      { id: number | string; formData: Record<string, any> }
    >({
      query: ({ id, formData }) => ({
        url: `api/sources/${id}/host`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    removeHost: build.mutation<any, number | string>({
      query: (id) => ({
        url: `api/sources/${id}/host`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => sourceTag(id),
    }),
    addMPC: build.mutation<
      any,
      { id: number | string; formData: Record<string, any> }
    >({
      query: ({ id, formData }) => ({
        url: `api/sources/${id}/mpc`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    addGCNCrossmatch: build.mutation<
      any,
      { id: number | string; formData: Record<string, any> }
    >({
      query: ({ id, formData }) => ({
        url: `api/sources/${id}/gcn_event`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),

    // ----- Analyses (start / delete) -----
    startAnalysis: build.mutation<
      RouteData<"POST /api/{analysis_resource_type}/{resource_id}/analysis/{analysis_service_id}">,
      {
        id: number | string;
        analysis_service_id: number | string;
        formData?: Record<string, any> | undefined;
      }
    >({
      query: ({ id, analysis_service_id, formData = {} }) => ({
        url: `api/obj/${id}/analysis/${analysis_service_id}`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["Source"],
    }),
    deleteAnalysis: build.mutation<
      any,
      {
        analysis_id: number | string;
        formData?: Record<string, any> | undefined;
      }
    >({
      query: ({ analysis_id, formData = {} }) => ({
        url: `api/obj/analysis/${analysis_id}`,
        method: "DELETE",
        body: formData,
      }),
      invalidatesTags: ["Source"],
    }),
  }),
});

// Websocket-driven invalidation. The old handler conditionally re-fetched the
// loaded source (and its sub-resources) when a REFRESH message matched the
// loaded source's internal_key.
//
// REFRESH_SOURCE is broadcast to every connected client (`push_all`) carrying
// the changed source's `internal_key` as `obj_key`. We translate that to the
// obj id of the matching cached `getSource` entry and invalidate only that
// source's per-id tag — so a change to one source no longer forces every other
// client to refetch its own (heavy) source object. When no cached source
// matches (this client isn't viewing that source), there is nothing to refetch,
// which restores the original "only if it matches the loaded source" gate.
invalidateOnMessage(REFRESH_SOURCE, (payload, getState) => {
  const objKey = payload?.obj_key;
  if (!objKey) {
    return ["Source"];
  }
  const objId = findCachedQueryArg(
    getState,
    "getSource",
    (data) => data?.internal_key === objKey,
  ) as string | number | null;
  return objId != null ? [{ type: "Source", id: objId }] : null;
});
// REFRESH_SOURCE_POSITION is likewise broadcast to all clients with the
// changed source's internal_key; translate to the obj id and invalidate only
// that source's position cache entry (its own tag, so the heavy source object
// is not refetched on a position change).
invalidateOnMessage(REFRESH_SOURCE_POSITION, (payload, getState) => {
  const objKey = payload?.obj_key;
  if (!objKey) {
    return ["Source"];
  }
  const objId = findCachedQueryArg(
    getState,
    "getSource",
    (data) => data?.internal_key === objKey,
  ) as string | number | null;
  return objId != null ? [{ type: "SourcePosition", id: objId }] : null;
});
invalidateOnMessage(REFRESH_OBJ_ANALYSES, () => ["Source"]);

export const {
  useGetSourceQuery,
  useGetObjGroupsQuery,
  useLazyGetSourceQuery,
  useGetSourcePositionQuery,
  useGetAssociatedGcnsQuery,
  useGetAnalysesQuery,
  useGetAnalysisQuery,
  useLazyGetAnalysisQuery,
  useGetAnalysisResultsQuery,
  useLazyGetAnalysisResultsQuery,
  useCheckSourceMutation,
  useGetPhotometryRequestQuery,
  useLazyGetPhotometryRequestQuery,
  useGetSourceFinderChartQuery,
  useLazyGetSourceFinderChartQuery,
  useGetCommentTextAttachmentQuery,
  useLazyGetCommentTextAttachmentQuery,
  useGetCommentOnSpectrumTextAttachmentQuery,
  useLazyGetCommentOnSpectrumTextAttachmentQuery,
  useSaveSourceMutation,
  useUpdateSourceMutation,
  useUpdateSourceGroupsMutation,
  useAcceptSaveRequestMutation,
  useDeclineSaveRequestMutation,
  useAddSourceViewMutation,
  useAddClassificationMutation,
  useDeleteClassificationMutation,
  useDeleteClassificationsMutation,
  useAddClassificationVoteMutation,
  useAddCommentMutation,
  useEditCommentMutation,
  useDeleteCommentMutation,
  useDeleteCommentOnSpectrumMutation,
  useAddAnnotationMutation,
  useDeleteAnnotationMutation,
  useAddSourceLabelsMutation,
  useDeleteSourceLabelsMutation,
  useSubmitFollowupRequestMutation,
  useEditFollowupRequestMutation,
  useDeleteFollowupRequestMutation,
  useSubmitAssignmentMutation,
  useEditAssignmentMutation,
  useDeleteAssignmentMutation,
  useSendAlertMutation,
  useShareDataMutation,
  useUploadPhotometryMutation,
  useCopySourcePhotometryMutation,
  useFetchGaiaMutation,
  useFetchWiseMutation,
  useFetchVizierMutation,
  useFetchPhotozMutation,
  useFetchPS1Mutation,
  useAddTNSMutation,
  useAddHostMutation,
  useRemoveHostMutation,
  useAddMPCMutation,
  useAddGCNCrossmatchMutation,
  useStartAnalysisMutation,
  useDeleteAnalysisMutation,
} = sourceApi;
