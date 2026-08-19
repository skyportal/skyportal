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
import type { AnalysisPost, ObjAnalysis } from "skyportal-js/Analysis";
import type {
  AssignmentPost,
  UpdateAssignmentOptions,
} from "skyportal-js/Assignments";
import type {
  ClassificationPost,
  ClassificationUpdate,
} from "skyportal-js/Classifications";
import type { Comment, CommentAttachment } from "skyportal-js/Comments";
import type {
  FollowupRequestPost,
  UpdateFollowupRequestOptions,
} from "skyportal-js/FollowupRequests";
import type { ObjPosition } from "skyportal-js/Objs";
import type { SourceGroupsPost } from "skyportal-js/SourceGroups";
import type {
  FinderChartFacility,
  Source,
  SourceExists,
  SourceFinderChart,
  SourceGcnEventCrossmatchPost,
  SourceMpcQueryPost,
  SourceNotificationPost,
  SourcePost,
  SourceSavedGroup,
  UpdateSourceOptions,
} from "skyportal-js/Sources";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage, findCachedQueryArg } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";
import { sourceTag } from "./sourceTags";

export const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";
export const REFRESH_SOURCE_POSITION = "skyportal/REFRESH_SOURCE_POSITION";
export const REFRESH_OBJ_ANALYSES = "skyportal/REFRESH_OBJ_ANALYSES";

export type SourcePosition = ObjPosition;

export type AssociatedGcns = string[];

export type { CommentAttachment };

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
    getSource: build.query<Source, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.fetchSource(String(id), sourceIncludeParams),
        ),
      // Provides both the broad "Source" tag (so the existing mutations, which
      // invalidate ["Source"], keep refetching) and a per-id tag so a websocket
      // REFRESH for one source invalidates only that source's cache entry.
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    // Lightweight: the groups an obj is currently saved/requested to (empty for an
    // unsaved candidate). Used to seed the toolbar save-to-groups dialog.
    getObjGroups: build.query<SourceSavedGroup[], number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchSourceSavedGroups(String(id))),
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    getSourcePosition: build.query<SourcePosition, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchObjPosition(String(id))),
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
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEventsAssociatedWithSource(String(id)),
        ),
      // Broad "Source" (so any broad source mutation still refetches it) plus a
      // per-id tag so per-source mutations (e.g. addGCNCrossmatch) refresh only
      // this source's associated GCNs.
      providesTags: (_result, _error, id) => ["Source", { type: "Source", id }],
    }),
    // `analysis_resource_type` is always "obj" (the only resource type the API
    // serves analyses for), so the client's obj-scoped endpoints cover it.
    getAnalyses: build.query<
      ObjAnalysis[],
      {
        analysis_resource_type?: string | undefined;
        params?:
          | {
              objID?: string;
              analysisServiceID?: number;
              summaryOnly?: boolean;
              includeFilename?: boolean;
            }
          | undefined;
      }
    >({
      queryFn: ({ params = {} }, api) =>
        clientQuery(api, (client) =>
          client.fetchAnalyses({
            objId: params.objID,
            analysisServiceId: params.analysisServiceID,
            summaryOnly: params.summaryOnly,
            includeFilename: params.includeFilename,
          }),
        ),
      providesTags: ["Source"],
    }),
    getAnalysis: build.query<
      ObjAnalysis,
      {
        analysis_id: number | string;
        analysis_resource_type?: string | undefined;
        params?:
          | { includeAnalysisData?: boolean; includeFilename?: boolean }
          | undefined;
      }
    >({
      queryFn: ({ analysis_id, params = {} }, api) =>
        clientQuery(api, (client) =>
          client.fetchAnalysis(Number(analysis_id), params),
        ),
    }),
    getAnalysisResults: build.query<
      Record<string, unknown>,
      {
        analysis_id: number | string;
        analysis_resource_type?: string | undefined;
      }
    >({
      queryFn: ({ analysis_id }, api) =>
        clientQuery(
          api,
          async (client) =>
            (await client.fetchAnalysisResults(Number(analysis_id))) as Record<
              string,
              unknown
            >,
        ),
    }),
    // An imperative one-off existence check (used in submit handlers via
    // `await checkSource(...).unwrap()`), so it's a mutation, not a lazy query:
    // a lazy-query trigger's `.unwrap()` in a handler can reject on subscription
    // teardown, which the callers' empty `catch` swallows — silently aborting
    // the subsequent saveSource.
    checkSource: build.mutation<
      SourceExists,
      {
        id: number | string;
        params: { nameOnly?: boolean; ra?: number; dec?: number };
      }
    >({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.fetchSourceExists({
            objId: String(id),
            ...(params.nameOnly
              ? {}
              : { ra: params.ra, dec: params.dec, radius: 0.0003 }),
          }),
        ),
    }),
    getPhotometryRequest: build.query<
      { request_status?: string | null | undefined },
      {
        id: number | string;
        params?: { refreshRequests?: boolean } | undefined;
      }
    >({
      queryFn: ({ id, params = {} }, api) =>
        clientQuery(api, (client) =>
          client.requestFollowupPhotometry(Number(id), {
            refreshRequests: params.refreshRequests,
          }),
        ),
    }),
    getSourceFinderChart: build.query<
      SourceFinderChart,
      { id: number | string; params: Record<string, any> }
    >({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.fetchSourceFinderJson(String(id), params),
        ),
    }),
    getFinderChartFacilities: build.query<
      Record<string, FinderChartFacility>,
      void
    >({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchFinderChartFacilities()),
    }),
    // The empty download/preview values are what select the JSON form; any
    // non-empty value (even "false") reads as truthy server-side.
    getCommentTextAttachment: build.query<
      CommentAttachment,
      { sourceID: number | string; commentID: number | string }
    >({
      queryFn: ({ sourceID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.fetchCommentAttachmentText(sourceID, Number(commentID)),
        ),
    }),
    getCommentOnSpectrumTextAttachment: build.query<
      CommentAttachment,
      { spectrumID: number | string; commentID: number | string }
    >({
      queryFn: ({ spectrumID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.fetchCommentAttachmentText(spectrumID, Number(commentID), {
            resourceType: "spectra",
          }),
        ),
    }),

    // ----- Save / update / transfer -----
    saveSource: build.mutation<{ id: string }, SourcePost>({
      queryFn: (payload, api) =>
        clientQuery(api, (client) => client.postSource(payload)),
      invalidatesTags: ["Source"],
    }),
    updateSource: build.mutation<
      void,
      {
        id: number | string;
        // alias/t0/tns_name land in UpdateSourceOptions with skyportal-js#6;
        // the handler already loads them through the Obj schema.
        payload: UpdateSourceOptions & {
          alias?: string[];
          t0?: number | null;
          tns_name?: string;
        };
      }
    >({
      queryFn: ({ id, payload }, api) =>
        clientQuery(api, (client) => client.updateSource(String(id), payload)),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    updateSourceGroups: build.mutation<void, SourceGroupsPost>({
      queryFn: (payload, api) =>
        clientQuery(api, (client) => client.postSourceGroups(payload)),
      invalidatesTags: ["Source"],
    }),
    acceptSaveRequest: build.mutation<
      void,
      { sourceID: number | string; groupID: number | string }
    >({
      queryFn: ({ sourceID, groupID }, api) =>
        clientQuery(api, (client) =>
          client.updateSourceGroup(
            String(sourceID),
            Number(groupID),
            true,
            false,
          ),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    declineSaveRequest: build.mutation<
      void,
      { sourceID: number | string; groupID: number | string }
    >({
      queryFn: ({ sourceID, groupID }, api) =>
        clientQuery(api, (client) =>
          client.updateSourceGroup(
            String(sourceID),
            Number(groupID),
            false,
            false,
          ),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    addSourceView: build.mutation<any, number | string>({
      query: (id) => ({
        url: `api/internal/source_views/${id}`,
        method: "POST",
      }),
    }),

    // ----- Classifications -----
    addClassification: build.mutation<
      { classification_id: number },
      ClassificationPost
    >({
      queryFn: (formData, api) =>
        clientQuery(api, (client) => client.postClassification(formData)),
      invalidatesTags: (_result, _error, formData) =>
        sourceTag(formData?.obj_id),
    }),
    updateClassification: build.mutation<
      void,
      {
        classificationID: number | string;
        formData: ClassificationUpdate & { obj_id?: string };
      }
    >({
      queryFn: ({ classificationID, formData }, api) =>
        clientQuery(api, (client) =>
          client.updateClassification(Number(classificationID), formData),
        ),
      invalidatesTags: (_result, _error, { formData }) =>
        sourceTag(formData?.obj_id),
    }),
    deleteClassification: build.mutation<void, number | string>({
      queryFn: (classificationID, api) =>
        clientQuery(api, (client) =>
          client.deleteClassification(Number(classificationID)),
        ),
      invalidatesTags: ["Source"],
    }),
    deleteClassifications: build.mutation<void, number | string>({
      queryFn: (sourceID, api) =>
        clientQuery(api, (client) =>
          client.deleteSourceClassifications(String(sourceID)),
        ),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    addClassificationVote: build.mutation<
      void,
      {
        classification_id: number | string;
        data?: { vote?: number } | undefined;
      }
    >({
      queryFn: ({ classification_id, data = {} }, api) =>
        clientQuery(api, (client) =>
          client.postClassificationVote(
            Number(classification_id),
            data.vote ?? 1,
          ),
        ),
      invalidatesTags: ["Source"],
    }),

    // ----- Comments -----
    // raw: comments carry a conversation `channel` the client cannot send yet
    // (skyportal-js#6 adds it)
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
    // raw until skyportal-js#6 ships fetchCommentChannels/deleteCommentChannel
    getConversations: build.query<string[], string>({
      query: (obj_id) => `api/sources/${obj_id}/comments/channels`,
      providesTags: (_result, _error, obj_id) => sourceTag(obj_id),
    }),
    getConversation: build.query<
      Comment[],
      { obj_id: string; channel: string }
    >({
      queryFn: ({ obj_id, channel }, api) =>
        clientQuery(api, (client) => client.fetchComments(obj_id, { channel })),
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
      void,
      { sourceID: number | string; commentID: number | string }
    >({
      queryFn: ({ sourceID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.deleteComment(sourceID, Number(commentID)),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    deleteCommentOnSpectrum: build.mutation<
      void,
      { spectrumID: number | string; commentID: number | string }
    >({
      queryFn: ({ spectrumID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.deleteComment(spectrumID, Number(commentID), {
            resourceType: "spectra",
          }),
        ),
      invalidatesTags: ["Source"],
    }),

    // ----- Annotations -----
    addAnnotation: build.mutation<
      { annotation_id: number },
      {
        sourceID: number | string;
        formData: {
          origin: string;
          data: Record<string, unknown>;
          group_ids?: number[];
        };
      }
    >({
      queryFn: ({ sourceID, formData }, api) =>
        clientQuery(api, (client) =>
          client.postAnnotation(sourceID, formData.origin, formData.data, {
            groupIds: formData.group_ids,
          }),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    deleteAnnotation: build.mutation<
      void,
      { sourceID: number | string; annotationID: number | string }
    >({
      queryFn: ({ sourceID, annotationID }, api) =>
        clientQuery(api, (client) =>
          client.deleteAnnotation(sourceID, Number(annotationID)),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),

    // ----- Labels -----
    addSourceLabels: build.mutation<
      void,
      { id: number | string; data: { groupIds: number[] } }
    >({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.postSourceLabels(String(id), data.groupIds),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    deleteSourceLabels: build.mutation<
      void,
      { id: number | string; data: { groupIds: number[] } }
    >({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.deleteSourceLabels(String(id), data.groupIds),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),

    // ----- Follow-up requests -----
    submitFollowupRequest: build.mutation<
      { id: number },
      FollowupRequestPost & { instrument_name?: string }
    >({
      queryFn: ({ instrument_name, ...paramsToSubmit }, api) =>
        clientQuery(api, (client) =>
          client.postFollowupRequest(paramsToSubmit),
        ),
      invalidatesTags: ["Source"],
    }),
    editFollowupRequest: build.mutation<
      void,
      {
        params: UpdateFollowupRequestOptions & { instrument_name?: string };
        requestID: number | string;
      }
    >({
      queryFn: ({ params, requestID }, api) => {
        const { instrument_name, ...paramsToSubmit } = params;
        return clientQuery(api, (client) =>
          client.updateFollowupRequest(Number(requestID), paramsToSubmit),
        );
      },
      invalidatesTags: ["Source"],
    }),
    deleteFollowupRequest: build.mutation<
      void,
      { id: number | string; params?: Record<string, unknown> | undefined }
    >({
      queryFn: ({ id }, api) =>
        clientQuery(api, (client) => client.deleteFollowupRequest(Number(id))),
      invalidatesTags: ["Source"],
    }),

    // ----- Assignments -----
    submitAssignment: build.mutation<{ id: number }, AssignmentPost>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.postAssignment(params)),
      invalidatesTags: ["Source"],
    }),
    editAssignment: build.mutation<
      void,
      { params: UpdateAssignmentOptions; assignmentID: number | string }
    >({
      queryFn: ({ params, assignmentID }, api) =>
        clientQuery(api, (client) =>
          client.updateAssignment(Number(assignmentID), params),
        ),
      invalidatesTags: ["Source"],
    }),
    deleteAssignment: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteAssignment(Number(id))),
      invalidatesTags: ["Source"],
    }),

    // ----- Notifications / sharing / photometry -----
    sendAlert: build.mutation<{ id: number }, SourceNotificationPost>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.postSourceNotification(params)),
    }),
    shareData: build.mutation<
      void,
      {
        groupIDs: number[];
        photometryIDs?: number[];
        spectrumIDs?: number[];
      }
    >({
      queryFn: ({ groupIDs, photometryIDs, spectrumIDs }, api) =>
        clientQuery(api, (client) =>
          client.postSharing(groupIDs, {
            photometryIds: photometryIDs,
            spectrumIds: spectrumIDs,
          }),
        ),
    }),
    // raw: the client's postPhotometry cannot send `refresh` yet
    // (skyportal-js#6 adds it)
    uploadPhotometry: build.mutation<any, Record<string, any>>({
      query: (data) => ({
        url: "api/photometry?refresh=true",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Source"],
    }),
    copySourcePhotometry: build.mutation<
      void,
      {
        id: number | string;
        formData: { origin_id: string; group_ids: number[] };
      }
    >({
      queryFn: ({ id, formData }, api) =>
        clientQuery(api, (client) =>
          client.postSourcePhotometryCopy(
            String(id),
            formData.origin_id,
            formData.group_ids,
          ),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),

    // ----- External-catalog annotations -----
    fetchGaia: build.mutation<void, number | string>({
      queryFn: (sourceID, api) =>
        clientQuery(api, (client) =>
          client.postGaiaAnnotation(String(sourceID)),
        ),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    fetchWise: build.mutation<void, number | string>({
      queryFn: (sourceID, api) =>
        clientQuery(api, (client) =>
          client.postIrsaAnnotation(String(sourceID)),
        ),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),
    fetchVizier: build.mutation<
      void,
      { sourceID: number | string; catalog?: string | undefined }
    >({
      queryFn: ({ sourceID, catalog = "VII/290" }, api) =>
        clientQuery(api, (client) =>
          client.postVizierAnnotation(String(sourceID), { catalog }),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    fetchDatalab: build.mutation<
      void,
      { sourceID: number | string; catalog?: string | undefined }
    >({
      queryFn: ({ sourceID, catalog = "ls_dr10" }, api) =>
        clientQuery(api, (client) =>
          client.postDatalabAnnotation(String(sourceID), { catalog }),
        ),
      invalidatesTags: (_result, _error, { sourceID }) => sourceTag(sourceID),
    }),
    fetchPS1: build.mutation<void, number | string>({
      queryFn: (sourceID, api) =>
        clientQuery(api, (client) =>
          client.postPs1Annotation(String(sourceID)),
        ),
      invalidatesTags: (_result, _error, sourceID) => sourceTag(sourceID),
    }),

    // ----- TNS / host / MPC / GCN crossmatch -----
    addTNS: build.mutation<
      void,
      {
        id: number | string;
        formData: { radius?: number; tnsrobot_id?: number };
      }
    >({
      queryFn: ({ id, formData }, api) =>
        clientQuery(api, (client) =>
          client.fetchSourceTns(String(id), formData),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    addHost: build.mutation<
      void,
      { id: number | string; formData: { galaxyName: string } }
    >({
      queryFn: ({ id, formData }, api) =>
        clientQuery(api, (client) =>
          client.postSourceHost(String(id), formData.galaxyName),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    removeHost: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteSourceHost(String(id))),
      invalidatesTags: (_result, _error, id) => sourceTag(id),
    }),
    addMPC: build.mutation<
      void,
      { id: number | string; formData: SourceMpcQueryPost }
    >({
      queryFn: ({ id, formData }, api) =>
        clientQuery(api, (client) =>
          client.postSourceMpcQuery(String(id), formData),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),
    addGCNCrossmatch: build.mutation<
      void,
      { id: number | string; formData: SourceGcnEventCrossmatchPost }
    >({
      queryFn: ({ id, formData }, api) =>
        clientQuery(api, (client) =>
          client.postSourceGcnEventCrossmatch(String(id), formData),
        ),
      invalidatesTags: (_result, _error, { id }) => sourceTag(id),
    }),

    // ----- Analyses (start / delete) -----
    startAnalysis: build.mutation<
      { id: number },
      {
        id: number | string;
        analysis_service_id: number | string;
        formData?: AnalysisPost | undefined;
      }
    >({
      queryFn: ({ id, analysis_service_id, formData = {} }, api) =>
        clientQuery(api, (client) =>
          client.postAnalysis(
            String(id),
            Number(analysis_service_id),
            formData,
          ),
        ),
      invalidatesTags: ["Source"],
    }),
    deleteAnalysis: build.mutation<void, { analysis_id: number | string }>({
      queryFn: ({ analysis_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteAnalysis(Number(analysis_id)),
        ),
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
} = sourceApi;
