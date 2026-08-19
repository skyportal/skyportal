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
import type { CommentAttachment } from "skyportal-js/Comments";
import type {
  GcnCatalogQuery,
  GcnEvent,
  GcnEventIdResponse,
  GcnEventPost,
  GcnEventPostResponse,
  GcnEventTachInfo,
  GcnReport,
  GcnReportPost,
  GcnSummary,
  GcnSummaryPost,
  GcnTrigger,
} from "skyportal-js/GcnEvents";
import type {
  ObservationPlanIdsResponse,
  ObservationPlanPost,
  ObservationPlanRequest,
} from "skyportal-js/ObservationPlans";
import type { SurveyEfficiencyForObservations } from "skyportal-js/SurveyEfficiency";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

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

export const gcnEventApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // ----- Main event + read-only sub-fetches -----
    getGcnEvent: build.query<GcnEvent, string>({
      queryFn: (dateobs, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEvent(dateobs, { excludeNoticeContent: true }),
        ),
      // Broad "GcnEvent" tag (so mutations / other REFRESH_* events still
      // refetch) plus a per-id tag keyed by dateobs, so REFRESH_GCN_EVENT only
      // refetches the event a client is actually viewing.
      providesTags: (_result, _error, dateobs) => [
        "GcnEvent",
        { type: "GcnEvent", id: dateobs },
      ],
    }),
    getGcnTach: build.query<GcnEventTachInfo, string>({
      queryFn: (dateobs, api) =>
        clientQuery(api, (client) => client.fetchGcnEventTach(dateobs)),
      providesTags: (_result, _error, dateobs) => [
        "GcnEvent",
        { type: "GcnEvent", id: dateobs },
      ],
    }),
    getGcnTrigger: build.query<
      GcnTrigger[],
      { dateobs: string; allocationID?: number | string | null }
    >({
      queryFn: ({ dateobs, allocationID = null }, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEventTriggers(dateobs, {
            ...(allocationID ? { allocationId: Number(allocationID) } : {}),
          }),
        ),
      providesTags: ["GcnEvent"],
    }),
    getGcnEventSurveyEfficiency: build.query<
      SurveyEfficiencyForObservations[],
      { gcnID: number | string }
    >({
      queryFn: ({ gcnID }, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEventSurveyEfficiency(Number(gcnID)),
        ),
      providesTags: ["GcnEvent"],
    }),
    getGcnEventCatalogQueries: build.query<
      GcnCatalogQuery[],
      { gcnID: number | string }
    >({
      queryFn: ({ gcnID }, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEventCatalogQueries(Number(gcnID)),
        ),
      providesTags: ["GcnEvent"],
    }),
    getObservationPlanRequests: build.query<
      ObservationPlanRequest[],
      number | string
    >({
      queryFn: (gcnEventID, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnEventObservationPlanRequests(Number(gcnEventID)),
        ),
      providesTags: ["GcnEvent"],
    }),
    getObservationPlan: build.query<ObservationPlanRequest, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.fetchObservationPlan(Number(id), {
            includePlannedObservations: true,
          }),
        ),
    }),
    getGcnEventReport: build.query<
      GcnReport,
      { dateobs: string; reportID: number | string }
    >({
      queryFn: ({ dateobs, reportID }, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnReport(dateobs, Number(reportID)),
        ),
      providesTags: ["GcnEvent"],
    }),
    getGcnEventReports: build.query<GcnReport[], string>({
      queryFn: (dateobs, api) =>
        clientQuery(api, (client) => client.fetchGcnReports(dateobs)),
      providesTags: ["GcnEvent"],
    }),
    getGcnEventSummary: build.query<
      GcnSummary,
      { dateobs: string; summaryID: number | string }
    >({
      queryFn: ({ dateobs, summaryID }, api) =>
        clientQuery(api, (client) =>
          client.fetchGcnSummary(dateobs, Number(summaryID)),
        ),
    }),
    // The empty download/preview values are what select the JSON form; any
    // non-empty value (even "false") reads as truthy server-side.
    getCommentOnGcnEventTextAttachment: build.query<
      CommentAttachment,
      { gcnEventID: number | string; commentID: number | string }
    >({
      queryFn: ({ gcnEventID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.fetchCommentAttachmentText(gcnEventID, Number(commentID), {
            resourceType: "gcn_event",
          }),
        ),
    }),

    // ----- Event-level mutations -----
    submitGcnEvent: build.mutation<GcnEventPostResponse, GcnEventPost>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.postGcnEvent(data)),
      invalidatesTags: ["GcnEvent"],
    }),
    postGcnTach: build.mutation<GcnEventIdResponse, string>({
      queryFn: (dateobs, api) =>
        clientQuery(api, (client) => client.postGcnEventTach(dateobs)),
      invalidatesTags: ["GcnEvent"],
    }),
    postGcnGraceDB: build.mutation<GcnEventIdResponse, string>({
      queryFn: (dateobs, api) =>
        clientQuery(api, (client) => client.postGcnEventGracedb(dateobs)),
      invalidatesTags: ["GcnEvent"],
    }),
    postGcnAlias: build.mutation<
      void,
      { dateobs: string; params: { alias: string } }
    >({
      queryFn: ({ dateobs, params }, api) =>
        clientQuery(api, (client) =>
          client.postGcnEventAlias(dateobs, params.alias),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnAlias: build.mutation<
      void,
      { dateobs: string; params: { alias: string } }
    >({
      queryFn: ({ dateobs, params }, api) =>
        clientQuery(api, (client) =>
          client.deleteGcnEventAlias(dateobs, params.alias),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    putGcnTrigger: build.mutation<
      GcnTrigger,
      {
        dateobs: string;
        allocationID: number | string;
        triggered: boolean;
      }
    >({
      queryFn: ({ dateobs, allocationID, triggered }, api) =>
        clientQuery(api, (client) =>
          client.updateGcnEventTrigger(
            dateobs,
            Number(allocationID),
            triggered,
          ),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnTrigger: build.mutation<
      GcnTrigger,
      { dateobs: string; allocationID: number | string }
    >({
      queryFn: ({ dateobs, allocationID }, api) =>
        clientQuery(api, (client) =>
          client.deleteGcnEventTrigger(dateobs, Number(allocationID)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Comments -----
    addCommentOnGcnEvent: build.mutation<
      { comment_id: number },
      {
        gcnevent_id: number | string;
        text: string;
        group_ids?: number[];
        attachment?: File;
      }
    >({
      queryFn: async ({ gcnevent_id, text, group_ids, attachment }, api) => {
        const file = attachment
          ? await fileReaderPromise(attachment)
          : undefined;
        return clientQuery(api, (client) =>
          file
            ? client.postCommentWithAttachment(
                gcnevent_id,
                text,
                file.name,
                String(file.body),
                { resourceType: "gcn_event", groupIds: group_ids },
              )
            : client.postComment(gcnevent_id, text, {
                resourceType: "gcn_event",
                groupIds: group_ids,
              }),
        );
      },
      invalidatesTags: ["GcnEvent"],
    }),
    editCommentOnGcnEvent: build.mutation<
      void,
      {
        commentID: number | string;
        gcnEventID: number | string;
        formData: {
          text?: string;
          group_ids?: number[];
          attachment?: File;
        };
      }
    >({
      queryFn: async ({ commentID, gcnEventID, formData }, api) => {
        const file = formData.attachment
          ? await fileReaderPromise(formData.attachment)
          : undefined;
        return clientQuery(api, (client) =>
          client.updateComment(gcnEventID, Number(commentID), {
            resourceType: "gcn_event",
            text: formData.text,
            groupIds: formData.group_ids,
            ...(file
              ? { attachmentName: file.name, attachmentBody: String(file.body) }
              : {}),
          }),
        );
      },
      invalidatesTags: ["GcnEvent"],
    }),
    deleteCommentOnGcnEvent: build.mutation<
      void,
      { gcnEventID: number | string; commentID: number | string }
    >({
      queryFn: ({ gcnEventID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.deleteComment(gcnEventID, Number(commentID), {
            resourceType: "gcn_event",
          }),
        ),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Observation plan requests -----
    // The form submits a batch (one plan per queued allocation), which the
    // handler takes as `observation_plans` + `combine_plans`.
    submitObservationPlanRequest: build.mutation<
      ObservationPlanIdsResponse,
      { observation_plans: ObservationPlanPost[]; combine_plans?: boolean }
    >({
      queryFn: ({ observation_plans, combine_plans }, api) =>
        clientQuery(api, (client) =>
          client.postObservationPlans(observation_plans, {
            combinePlans: combine_plans,
          }),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    sendObservationPlanRequest: build.mutation<
      ObservationPlanRequest | null,
      number | string
    >({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.postObservationPlanQueue(Number(id)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    removeObservationPlanRequest: build.mutation<
      ObservationPlanRequest,
      number | string
    >({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.deleteObservationPlanQueue(Number(id)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteObservationPlanRequest: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteObservationPlan(Number(id))),
      invalidatesTags: ["GcnEvent"],
    }),
    submitObservationPlanRequestTreasureMap: build.mutation<
      void,
      number | string
    >({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.postObservationPlanTreasuremap(Number(id)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteObservationPlanRequestTreasureMap: build.mutation<
      void,
      number | string
    >({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.deleteObservationPlanTreasuremap(Number(id)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    createObservationPlanRequestObservingRun: build.mutation<
      void,
      { id: number | string; params?: { groupIds?: number[] } | undefined }
    >({
      queryFn: ({ id, params = {} }, api) =>
        clientQuery(api, (client) =>
          client.postObservationPlanObservingRun(Number(id), params),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteObservationPlanFields: build.mutation<
      void,
      { id: number | string; fieldIds: number[] }
    >({
      queryFn: ({ id, fieldIds }, api) =>
        clientQuery(api, (client) =>
          client.deleteObservationPlanFields(Number(id), fieldIds),
        ),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Summaries -----
    postGcnEventSummary: build.mutation<
      GcnEventIdResponse,
      { dateobs: string; params: GcnSummaryPost }
    >({
      queryFn: ({ dateobs, params }, api) =>
        clientQuery(api, (client) => client.postGcnSummary(dateobs, params)),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnEventSummary: build.mutation<
      void,
      { dateobs: string; summaryID: number | string }
    >({
      queryFn: ({ dateobs, summaryID }, api) =>
        clientQuery(api, (client) =>
          client.deleteGcnSummary(dateobs, Number(summaryID)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    patchGcnEventSummary: build.mutation<
      GcnSummary,
      {
        dateobs: string;
        summaryID: number | string;
        formData: { body: string };
      }
    >({
      queryFn: ({ dateobs, summaryID, formData }, api) =>
        clientQuery(api, (client) =>
          client.updateGcnSummary(dateobs, Number(summaryID), formData.body),
        ),
      invalidatesTags: ["GcnEvent"],
    }),

    // ----- Reports -----
    postGcnEventReport: build.mutation<
      GcnEventIdResponse,
      { dateobs: string; params: GcnReportPost }
    >({
      queryFn: ({ dateobs, params }, api) =>
        clientQuery(api, (client) => client.postGcnReport(dateobs, params)),
      invalidatesTags: ["GcnEvent"],
    }),
    deleteGcnEventReport: build.mutation<
      void,
      { dateobs: string; reportID: number | string }
    >({
      queryFn: ({ dateobs, reportID }, api) =>
        clientQuery(api, (client) =>
          client.deleteGcnReport(dateobs, Number(reportID)),
        ),
      invalidatesTags: ["GcnEvent"],
    }),
    patchGcnEventReport: build.mutation<
      GcnReport,
      {
        dateobs: string;
        reportID: number | string;
        formData: { data?: Record<string, unknown>; published?: boolean };
      }
    >({
      queryFn: ({ dateobs, reportID, formData }, api) =>
        clientQuery(api, (client) =>
          client.updateGcnReport(dateobs, Number(reportID), formData),
        ),
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
