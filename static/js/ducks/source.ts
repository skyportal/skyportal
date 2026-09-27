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
import { buildQueryString } from "../API";
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
  includeSuperObjs: true,
};

export const sourceApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSource: build.query<
      RouteData<"GET /api/sources/{obj_id}">,
      number | string
    >({
      query: (id) => {
        const queryString = buildQueryString(sourceIncludeParams);
        return `api/sources/${id}?${queryString}`;
      },
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    getObjGroups: build.query<any[], number | string>({
      query: (id) => `api/sources/${id}/groups`,
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    getSourcePosition: build.query<SourcePosition, number | string>({
      query: (id) => `api/sources/${id}/position`,
      // Its own tag: a REFRESH_SOURCE from e.g. a comment must not refetch the position.
      providesTags: (_result, _error, id) => [
        "Source",
        { type: "Source", id },
        { type: "SourcePosition", id },
      ],
    }),
    getSourceAcknowledgment: build.query<any, Record<string, any>>({
      query: ({ id, ...selection }) => {
        // Omitted means "everything detected" server-side; an explicit empty list is not.
        const params = buildQueryString(
          Object.fromEntries(
            Object.entries(selection).filter(([, v]) => v !== undefined),
          ),
        );
        return `api/sources/${id}/acknowledgment${params ? `?${params}` : ""}`;
      },
      providesTags: (_result, _error, { id }) => [
        "Source",
        { type: "Source", id },
      ],
    }),
    getAssociatedGcns: build.query<AssociatedGcns, number | string>({
      query: (id) => `api/associated_gcns/${id}`,
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
      providesTags: (_result, _error, arg) =>
        arg?.analysis_resource_type === "gcn_event" ? ["GcnEvent"] : ["Source"],
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
    // A mutation, not a lazy query: a lazy trigger's unwrap() rejects on teardown.
    checkSource: build.mutation<
      any,
      { id: number | string; params: Record<string, any> }
    >({
      query: ({ id, params }) => {
        const queryParams =
          params["nameOnly"] || params["ra"] == null || params["dec"] == null
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
    getFinderChartFacilities: build.query<Record<string, any>, void>({
      query: () => "api/finder_chart/facilities",
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
      invalidatesTags: (_result, _error, { sourceID }) => [
        ...sourceTag(sourceID),
        "Sources",
      ],
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
      invalidatesTags: (_result, _error, { sourceID }) => [
        ...sourceTag(sourceID),
        "Sources",
      ],
    }),
    addSourceView: build.mutation<any, number | string>({
      query: (id) => ({
        url: `api/internal/source_views/${id}`,
        method: "POST",
      }),
    }),
    addClassification: build.mutation<any, Record<string, any>>({
      query: (formData) => ({
        url: "api/classification",
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _error, formData) =>
        sourceTag(formData?.["obj_id"]),
    }),
    updateClassification: build.mutation<
      any,
      { classificationID: number | string; formData: Record<string, any> }
    >({
      query: ({ classificationID, formData }) => ({
        url: `api/classification/${classificationID}`,
        method: "PUT",
        body: formData,
      }),
      invalidatesTags: (_result, _error, { formData }) =>
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
    addComment: build.mutation<
      RouteData<"POST /api/{associated_resource_type}/{resource_id}/comments">,
      Record<string, any>
    >({
      queryFn: async (formData, _api, _extra, baseQuery) => {
        const url = formData["spectrum_id"]
          ? `api/spectra/${formData["spectrum_id"]}/comments`
          : `api/sources/${formData["obj_id"]}/comments`;
        // Only the comment body keys; obj_id/spectrum_id are path params.
        const body: Record<string, any> = {};
        if (formData["text"] !== undefined) body["text"] = formData["text"];
        if (formData["group_ids"] !== undefined)
          body["group_ids"] = formData["group_ids"];
        if (formData["channel"] !== undefined)
          body["channel"] = formData["channel"];
        if (formData["origin"] !== undefined)
          body["origin"] = formData["origin"];
        if (formData["attachment"]) {
          body["attachment"] = await fileReaderPromise(formData["attachment"]);
        }
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
        const url = formData["spectrum_id"]
          ? `api/spectra/${formData["spectrum_id"]}/comments/${commentID}`
          : `api/sources/${formData["obj_id"]}/comments/${commentID}`;
        // Only the comment body keys; obj_id/spectrum_id are path params.
        const body: Record<string, any> = {};
        if (formData["text"] !== undefined) body["text"] = formData["text"];
        if (formData["group_ids"] !== undefined)
          body["group_ids"] = formData["group_ids"];
        if (formData["attachment"]) {
          body["attachment"] = await fileReaderPromise(formData["attachment"]);
        }
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
    getConversations: build.query<string[], string>({
      query: (obj_id) => `api/sources/${obj_id}/comments/channels`,
      providesTags: (_result, _error, obj_id) => sourceTag(obj_id),
    }),
    getConversation: build.query<any[], { obj_id: string; channel: string }>({
      query: ({ obj_id, channel }) =>
        `api/sources/${obj_id}/comments?channel=${encodeURIComponent(channel)}`,
      transformResponse: (data: any[]) =>
        (data ?? []).map(({ resourceType, ...comment }) => comment),
      providesTags: (_result, _error, { obj_id }) => sourceTag(obj_id),
    }),
    deleteConversation: build.mutation<
      any,
      { obj_id: string; channel: string }
    >({
      query: ({ obj_id, channel }) => ({
        url: `api/sources/${obj_id}/comments/channels?channel=${encodeURIComponent(channel)}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { obj_id }) => sourceTag(obj_id),
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
      invalidatesTags: ["Photometry", "Spectra"],
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
    fetchAlma: build.mutation<
      RouteData<"POST /api/sources/{obj_id}/annotations/alma">,
      number | string
    >({
      query: (sourceID) => ({
        url: `api/sources/${sourceID}/annotations/alma`,
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
    fetchDatalab: build.mutation<
      any,
      { sourceID: number | string; catalog?: string | undefined }
    >({
      query: ({ sourceID, catalog = "ls_dr10" }) => ({
        url: `api/sources/${sourceID}/annotations/datalab`,
        method: "POST",
        body: { catalog },
      }),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
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
    startAnalysis: build.mutation<
      RouteData<"POST /api/{analysis_resource_type}/{resource_id}/analysis/{analysis_service_id}">,
      {
        id: number | string;
        analysis_service_id: number | string;
        analysis_resource_type?: string;
        formData?: Record<string, any> | undefined;
      }
    >({
      query: ({
        id,
        analysis_service_id,
        analysis_resource_type = "obj",
        formData = {},
      }) => ({
        url: `api/${analysis_resource_type}/${id}/analysis/${analysis_service_id}`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["Source"],
    }),
    deleteAnalysis: build.mutation<
      any,
      {
        analysis_id: number | string;
        analysis_resource_type?: string;
        formData?: Record<string, any> | undefined;
      }
    >({
      query: ({
        analysis_id,
        analysis_resource_type = "obj",
        formData = {},
      }) => ({
        url: `api/${analysis_resource_type}/analysis/${analysis_id}`,
        method: "DELETE",
        body: formData,
      }),
      invalidatesTags: ["Source"],
    }),
    updateAnalysis: build.mutation<
      any,
      {
        analysis_id: number | string;
        group_ids: number[];
      }
    >({
      query: ({ analysis_id, group_ids }) => ({
        url: `api/obj/analysis/${analysis_id}`,
        method: "PATCH",
        body: { group_ids },
      }),
      invalidatesTags: ["Source"],
    }),
  }),
});

// Broadcast to every client: invalidate only the source this one has cached, if any.
const invalidateCachedSource =
  (type: "Source" | "SourcePosition") =>
  (payload: any, getState: () => unknown) => {
    const objKey = payload?.obj_key;
    if (!objKey) return ["Source" as const];
    const objId = findCachedQueryArg(
      getState,
      "getSource",
      (data) => data?.internal_key === objKey,
    ) as string | number | null;
    return objId != null ? [{ type, id: objId }] : null;
  };

invalidateOnMessage(REFRESH_SOURCE, invalidateCachedSource("Source"));
invalidateOnMessage(
  REFRESH_SOURCE_POSITION,
  invalidateCachedSource("SourcePosition"),
);
invalidateOnMessage(REFRESH_OBJ_ANALYSES, () => ["Source"]);
invalidateOnMessage("skyportal/REFRESH_GCNEVENT", () => ["GcnEvent"]);

export const {
  useGetSourceQuery,
  useGetObjGroupsQuery,
  useGetSourceAcknowledgmentQuery,
  useGetSourcePositionQuery,
  useGetAssociatedGcnsQuery,
  useGetAnalysesQuery,
  useGetAnalysisQuery,
  useGetAnalysisResultsQuery,
  useCheckSourceMutation,
  useLazyGetPhotometryRequestQuery,
  useLazyGetSourceFinderChartQuery,
  useGetFinderChartFacilitiesQuery,
  useLazyGetCommentTextAttachmentQuery,
  useLazyGetCommentOnSpectrumTextAttachmentQuery,
  useSaveSourceMutation,
  useUpdateSourceMutation,
  useUpdateSourceGroupsMutation,
  useAcceptSaveRequestMutation,
  useDeclineSaveRequestMutation,
  useAddSourceViewMutation,
  useAddClassificationMutation,
  useUpdateClassificationMutation,
  useDeleteClassificationMutation,
  useDeleteClassificationsMutation,
  useAddClassificationVoteMutation,
  useAddCommentMutation,
  useEditCommentMutation,
  useDeleteCommentMutation,
  useGetConversationsQuery,
  useGetConversationQuery,
  useDeleteConversationMutation,
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
  useFetchAlmaMutation,
  useFetchGaiaMutation,
  useFetchWiseMutation,
  useFetchVizierMutation,
  useFetchDatalabMutation,
  useFetchPS1Mutation,
  useAddTNSMutation,
  useAddHostMutation,
  useRemoveHostMutation,
  useAddMPCMutation,
  useAddGCNCrossmatchMutation,
  useStartAnalysisMutation,
  useDeleteAnalysisMutation,
  useUpdateAnalysisMutation,
} = sourceApi;
