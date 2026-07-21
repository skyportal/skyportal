/**
 * GCN event (the single loaded event detail + all its sub-resources).
 *
 * RTK Query conversion of the old composite `gcnEvent` duck. The old reducer
 * built ONE `gcnEvent` slice out of many independent sub-fetches (the main
 * event, tach circulars, triggered allocations, survey efficiency, catalog
 * queries, observation plan requests, a single observation plan, a single
 * report, and the report list). Here each sub-fetch becomes its own
 * `build.query`, keyed by its own argument and cached independently, and every
 * mutation (comments, aliases, triggers, observation plans, summaries, reports,
 * tach/gracedb) becomes its own `build.mutation`.
 *
 * Consumers that used to read `state.gcnEvent.<subfield>` now call the matching
 * query hook. Queries that surface event data provide the `GcnEvent` tag;
 * mutations that change event data invalidate it. The websocket `REFRESH_*`
 * messages are bridged to cache invalidation via `invalidateOnMessage`, so only
 * the active (currently-loaded) event's queries refetch.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export interface CommentAttachment {
  commentId: number | string;
  text: string;
  attachment: string;
  attachment_name: string;
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

export const gcnEventApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // ----- Main event + read-only sub-fetches -----
    getGcnEvent: build.query<RouteData<"GET /api/gcn_event/{dateobs}">, string>(
      {
        query: (dateobs) =>
          `api/gcn_event/${dateobs}?excludeNoticeContent=true`,
        // Broad "GcnEvent" tag (so mutations / other REFRESH_* events still
        // refetch) plus a per-id tag keyed by dateobs, so REFRESH_GCN_EVENT only
        // refetches the event a client is actually viewing.
        providesTags: (_result, _error, dateobs) => [
          "GcnEvent",
          { type: "GcnEvent", id: dateobs },
        ],
      },
    ),
    getGcnTach: build.query<{ circulars?: Record<string, string> }, string>({
      query: (dateobs) => `api/gcn_event/${dateobs}/tach`,
      providesTags: (_result, _error, dateobs) => [
        "GcnEvent",
        { type: "GcnEvent", id: dateobs },
      ],
    }),
    getGcnTrigger: build.query<
      any,
      { dateobs: string; allocationID?: number | string | null }
    >({
      query: ({ dateobs, allocationID = null }) =>
        allocationID
          ? `api/gcn_event/${dateobs}/triggered/${allocationID}`
          : `api/gcn_event/${dateobs}/triggered`,
      providesTags: ["GcnEvent"],
    }),
    getGcnEventSurveyEfficiency: build.query<
      RouteData<"GET /api/gcn_event/{gcnevent_id}/survey_efficiency">,
      { gcnID: number | string }
    >({
      query: ({ gcnID }) => `api/gcn_event/${gcnID}/survey_efficiency`,
      providesTags: ["GcnEvent"],
    }),
    getGcnEventCatalogQueries: build.query<
      RouteData<"GET /api/gcn_event/{gcnevent_id}/catalog_query">,
      { gcnID: number | string }
    >({
      query: ({ gcnID }) => `api/gcn_event/${gcnID}/catalog_query`,
      providesTags: ["GcnEvent"],
    }),
    getObservationPlanRequests: build.query<
      RouteData<"GET /api/gcn_event/{gcnevent_id}/observation_plan_requests">,
      number | string
    >({
      query: (gcnEventID) =>
        `api/gcn_event/${gcnEventID}/observation_plan_requests`,
      providesTags: ["GcnEvent"],
    }),
    getObservationPlan: build.query<
      RouteData<"GET /api/observation_plan/{observation_plan_request_id}">,
      number | string
    >({
      query: (id) =>
        `api/observation_plan/${id}?includePlannedObservations=true`,
    }),
    getGcnEventReport: build.query<
      RouteData<"GET /api/gcn_event/{dateobs}/report/{report_id}">,
      { dateobs: string; reportID: number | string }
    >({
      query: ({ dateobs, reportID }) =>
        `api/gcn_event/${dateobs}/report/${reportID}`,
      providesTags: ["GcnEvent"],
    }),
    getGcnEventReports: build.query<any, string>({
      query: (dateobs) => `api/gcn_event/${dateobs}/report`,
      providesTags: ["GcnEvent"],
    }),
    getGcnEventSummary: build.query<
      RouteData<"GET /api/gcn_event/{dateobs}/summary/{summary_id}">,
      { dateobs: string; summaryID: number | string }
    >({
      query: ({ dateobs, summaryID }) =>
        `api/gcn_event/${dateobs}/summary/${summaryID}`,
    }),
    getCommentOnGcnEventTextAttachment: build.query<
      CommentAttachment,
      { gcnEventID: number | string; commentID: number | string }
    >({
      query: ({ gcnEventID, commentID }) =>
        `api/gcn_event/${gcnEventID}/comments/${commentID}/attachment?download=false&preview=false`,
    }),

    // ----- Event-level mutations -----
    submitGcnEvent: build.mutation<RouteData<"POST /api/gcn_event">, any>({
      query: (data) => ({
        url: "api/gcn_event",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    postGcnTach: build.mutation<any, string>({
      query: (dateobs) => ({
        url: `api/gcn_event/${dateobs}/tach`,
        method: "POST",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    postGcnGraceDB: build.mutation<any, string>({
      query: (dateobs) => ({
        url: `api/gcn_event/${dateobs}/gracedb`,
        method: "POST",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    postGcnAlias: build.mutation<
      any,
      { dateobs: string; params?: Record<string, any> | undefined }
    >({
      query: ({ dateobs, params = {} }) => ({
        url: `api/gcn_event/${dateobs}/alias`,
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnAlias: build.mutation<
      any,
      { dateobs: string; params?: Record<string, any> | undefined }
    >({
      query: ({ dateobs, params = {} }) => ({
        url: `api/gcn_event/${dateobs}/alias`,
        method: "DELETE",
        body: params,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    putGcnTrigger: build.mutation<
      any,
      {
        dateobs: string;
        allocationID: number | string;
        triggered: boolean;
      }
    >({
      query: ({ dateobs, allocationID, triggered }) => ({
        url: `api/gcn_event/${dateobs}/triggered/${allocationID}`,
        method: "PUT",
        body: { triggered },
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnTrigger: build.mutation<
      any,
      { dateobs: string; allocationID: number | string }
    >({
      query: ({ dateobs, allocationID }) => ({
        url: `api/gcn_event/${dateobs}/triggered/${allocationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Comments -----
    addCommentOnGcnEvent: build.mutation<
      RouteData<"POST /api/{associated_resource_type}/{resource_id}/comments">,
      any
    >({
      queryFn: async (formData, _api, _extra, baseQuery) => {
        const body = { ...formData };
        if (body.attachment) {
          body.attachment = await fileReaderPromise(body.attachment);
        }
        const result = await baseQuery({
          url: `api/gcn_event/${body.gcnevent_id}/comments`,
          method: "POST",
          body,
        });
        if (result.error) {
          return { error: result.error };
        }
        return {
          data: result.data as RouteData<"POST /api/{associated_resource_type}/{resource_id}/comments">,
        };
      },
      invalidatesTags: ["GcnEvent"],
    }),
    editCommentOnGcnEvent: build.mutation<
      RouteData<"PUT /api/{associated_resource_type}/{resource_id}/comments/{comment_id}">,
      {
        commentID: number | string;
        gcnEventID: number | string;
        formData: any;
      }
    >({
      queryFn: async (
        { commentID, gcnEventID, formData },
        _api,
        _extra,
        baseQuery,
      ) => {
        const body = { ...formData };
        if (body.attachment) {
          body.attachment = await fileReaderPromise(body.attachment);
        }
        const result = await baseQuery({
          url: `api/gcn_event/${gcnEventID}/comments/${commentID}`,
          method: "PUT",
          body,
        });
        if (result.error) {
          return { error: result.error };
        }
        return {
          data: result.data as RouteData<"PUT /api/{associated_resource_type}/{resource_id}/comments/{comment_id}">,
        };
      },
      invalidatesTags: ["GcnEvent"],
    }),
    deleteCommentOnGcnEvent: build.mutation<
      any,
      { gcnEventID: number | string; commentID: number | string }
    >({
      query: ({ gcnEventID, commentID }) => ({
        url: `api/gcn_event/${gcnEventID}/comments/${commentID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Observation plan requests -----
    submitObservationPlanRequest: build.mutation<any, any>({
      query: (params) => {
        const { instrument_name, ...paramsToSubmit } = params;
        return {
          url: "api/observation_plan",
          method: "POST",
          body: paramsToSubmit,
        };
      },
      invalidatesTags: ["GcnEvent"],
    }),
    sendObservationPlanRequest: build.mutation<
      RouteData<"POST /api/observation_plan/{observation_plan_request_id}/queue">,
      number | string
    >({
      query: (id) => ({
        url: `api/observation_plan/${id}/queue`,
        method: "POST",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    removeObservationPlanRequest: build.mutation<
      RouteData<"DELETE /api/observation_plan/{observation_plan_request_id}/queue">,
      number | string
    >({
      query: (id) => ({
        url: `api/observation_plan/${id}/queue`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteObservationPlanRequest: build.mutation<any, number | string>({
      query: (id) => ({
        url: `api/observation_plan/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    submitObservationPlanRequestTreasureMap: build.mutation<
      any,
      number | string
    >({
      query: (id) => ({
        url: `api/observation_plan/${id}/treasuremap`,
        method: "POST",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteObservationPlanRequestTreasureMap: build.mutation<
      any,
      number | string
    >({
      query: (id) => ({
        url: `api/observation_plan/${id}/treasuremap`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    createObservationPlanRequestObservingRun: build.mutation<
      any,
      { id: number | string; params?: Record<string, any> | undefined }
    >({
      query: ({ id, params = {} }) => ({
        url: `api/observation_plan/${id}/observing_run`,
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteObservationPlanFields: build.mutation<
      RouteData<"DELETE /api/observation_plan/{observation_plan_request_id}/fields">,
      { id: number | string; fieldIds: any }
    >({
      query: ({ id, fieldIds }) => ({
        url: `api/observation_plan/${id}/fields`,
        method: "DELETE",
        body: { fieldIds },
      }),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Summaries -----
    postGcnEventSummary: build.mutation<
      any,
      { dateobs: string; params: Record<string, any> }
    >({
      query: ({ dateobs, params }) => ({
        url: `api/gcn_event/${dateobs}/summary`,
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnEventSummary: build.mutation<
      any,
      { dateobs: string; summaryID: number | string }
    >({
      query: ({ dateobs, summaryID }) => ({
        url: `api/gcn_event/${dateobs}/summary/${summaryID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    patchGcnEventSummary: build.mutation<
      any,
      { dateobs: string; summaryID: number | string; formData: any }
    >({
      query: ({ dateobs, summaryID, formData }) => ({
        url: `api/gcn_event/${dateobs}/summary/${summaryID}`,
        method: "PATCH",
        body: formData,
      }),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Reports -----
    postGcnEventReport: build.mutation<
      any,
      { dateobs: string; params: Record<string, any> }
    >({
      query: ({ dateobs, params }) => ({
        url: `api/gcn_event/${dateobs}/report`,
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnEventReport: build.mutation<
      any,
      { dateobs: string; reportID: number | string }
    >({
      query: ({ dateobs, reportID }) => ({
        url: `api/gcn_event/${dateobs}/report/${reportID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnEvent"],
    }),
    patchGcnEventReport: build.mutation<
      any,
      { dateobs: string; reportID: number | string; formData: any }
    >({
      query: ({ dateobs, reportID, formData }) => ({
        url: `api/gcn_event/${dateobs}/report/${reportID}`,
        method: "PATCH",
        body: formData,
      }),
      invalidatesTags: ["GcnEvent"],
    }),
  }),
});

// Websocket-driven invalidation. The old handler conditionally re-fetched the
// loaded event (and its sub-resources) when a REFRESH message matched the
// loaded event's dateobs / report id. With RTK Query, invalidating the
// `GcnEvent` tag only refetches the *active* queries — which are, by
// construction, the ones for the currently-loaded event — so the conditional
// "only if it matches the loaded event" guard is satisfied automatically.
invalidateOnMessage("skyportal/FETCH_GCNEVENT", () => ["GcnEvent"]);
// REFRESH_GCN_EVENT is broadcast to every client carrying the changed event's
// dateobs (which is exactly the getGcnEvent/getGcnTach query arg — no lookup
// needed). Invalidate only that event's per-id tag so other clients viewing a
// different event don't refetch their (heavy) event object. Restores the
// pre-migration "only if it matches the loaded event's dateobs" gate.
invalidateOnMessage("skyportal/REFRESH_GCN_EVENT", (payload) =>
  payload?.gcnEvent_dateobs != null
    ? [{ type: "GcnEvent", id: payload.gcnEvent_dateobs }]
    : ["GcnEvent"],
);
invalidateOnMessage("skyportal/REFRESH_GCN_TRIGGERED", () => ["GcnEvent"]);
invalidateOnMessage(
  "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
  () => ["GcnEvent"],
);
invalidateOnMessage("skyportal/REFRESH_GCNEVENT_CATALOG_QUERIES", () => [
  "GcnEvent",
]);
invalidateOnMessage("skyportal/REFRESH_GCNEVENT_SURVEY_EFFICIENCY", () => [
  "GcnEvent",
]);
invalidateOnMessage("skyportal/REFRESH_GCNEVENT_REPORT", () => ["GcnEvent"]);
invalidateOnMessage("skyportal/REFRESH_GCNEVENT_REPORTS", () => ["GcnEvent"]);

export const {
  useGetGcnEventQuery,
  useLazyGetGcnEventQuery,
  useGetGcnTachQuery,
  useGetGcnTriggerQuery,
  useGetGcnEventSurveyEfficiencyQuery,
  useGetGcnEventCatalogQueriesQuery,
  useGetObservationPlanRequestsQuery,
  useGetObservationPlanQuery,
  useLazyGetObservationPlanQuery,
  useGetGcnEventReportQuery,
  useLazyGetGcnEventReportQuery,
  useGetGcnEventReportsQuery,
  useGetGcnEventSummaryQuery,
  useLazyGetGcnEventSummaryQuery,
  useGetCommentOnGcnEventTextAttachmentQuery,
  useLazyGetCommentOnGcnEventTextAttachmentQuery,
  useSubmitGcnEventMutation,
  usePostGcnTachMutation,
  usePostGcnGraceDBMutation,
  usePostGcnAliasMutation,
  useDeleteGcnAliasMutation,
  usePutGcnTriggerMutation,
  useDeleteGcnTriggerMutation,
  useAddCommentOnGcnEventMutation,
  useEditCommentOnGcnEventMutation,
  useDeleteCommentOnGcnEventMutation,
  useSubmitObservationPlanRequestMutation,
  useSendObservationPlanRequestMutation,
  useRemoveObservationPlanRequestMutation,
  useDeleteObservationPlanRequestMutation,
  useSubmitObservationPlanRequestTreasureMapMutation,
  useDeleteObservationPlanRequestTreasureMapMutation,
  useCreateObservationPlanRequestObservingRunMutation,
  useDeleteObservationPlanFieldsMutation,
  usePostGcnEventSummaryMutation,
  useDeleteGcnEventSummaryMutation,
  usePatchGcnEventSummaryMutation,
  usePostGcnEventReportMutation,
  useDeleteGcnEventReportMutation,
  usePatchGcnEventReportMutation,
} = gcnEventApi;
