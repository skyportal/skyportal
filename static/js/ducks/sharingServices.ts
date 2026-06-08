/**
 * Sharing services (TNS / Hermes publishing configuration + submissions).
 *
 * RTK Query conversion of the old `FETCH_SHARING_SERVICES` /
 * `FETCH_SHARING_SERVICE_SUBMISSIONS` duck. The list and submissions are
 * queries; everything that creates/edits/deletes a sharing service, its groups,
 * auto publishers, coauthors, or a submission is a mutation that invalidates the
 * relevant tag so active queries refetch.
 *
 * The old websocket handler refetched the list on `REFRESH_SHARING_SERVICES`
 * (optionally scoped to a group) and refetched submissions on
 * `REFRESH_SHARING_SERVICE_SUBMISSIONS`; both are bridged to tag invalidation
 * via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type SharingService = Record<string, any>;

export interface SharingServiceSubmissions {
  sharing_service_id: number | string;
  submissions: any[];
  totalMatches: number;
  [key: string]: unknown;
}

interface FetchSharingServicesArg {
  group_id?: number | string | undefined;
  [key: string]: unknown;
}

interface FetchSubmissionsArg {
  sharing_service_id?: number | string | undefined;
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
  [key: string]: unknown;
}

interface AddSharingServiceGroupArg {
  sharing_service_id: number | string;
  data: any;
}

interface EditSharingServiceGroupArg {
  sharing_service_id: number | string;
  group_id: number | string;
  data: any;
}

interface DeleteSharingServiceGroupArg {
  sharing_service_id: number | string;
  group_id: number | string;
}

interface SharingServiceGroupAutoPublishersArg {
  sharing_service_id: number | string;
  group_id: number | string;
  user_ids?: any[] | undefined;
}

interface SharingServiceCoauthorArg {
  sharing_service_id: number | string;
  user_id: number | string;
}

interface EditSharingServiceArg {
  id: number | string;
  data: any;
}

export const sharingServicesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSharingServices: build.query<
      SharingService[],
      FetchSharingServicesArg | void
    >({
      query: (params) => ({
        url: "api/sharing_service",
        params: (params ?? {}) as Record<string, unknown>,
      }),
      providesTags: ["SharingService"],
    }),
    getSharingServiceSubmissions: build.query<
      SharingServiceSubmissions,
      FetchSubmissionsArg | void
    >({
      query: (params) => ({
        url: "api/sharing_service/submission",
        params: {
          ...((params ?? {}) as Record<string, unknown>),
          include_payload: true,
        },
      }),
      providesTags: ["SharingServiceSubmission"],
    }),
    addSharingService: build.mutation<unknown, any>({
      query: (data) => ({
        url: "api/sharing_service",
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["SharingService"],
    }),
    editSharingService: build.mutation<unknown, EditSharingServiceArg>({
      query: ({ id, data }) => ({
        url: `api/sharing_service/${id}`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingService: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/sharing_service/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceGroup: build.mutation<unknown, AddSharingServiceGroupArg>({
      query: ({ sharing_service_id, data }) => ({
        url: `api/sharing_service/${sharing_service_id}/group`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["SharingService"],
    }),
    editSharingServiceGroup: build.mutation<
      unknown,
      EditSharingServiceGroupArg
    >({
      query: ({ sharing_service_id, group_id, data }) => ({
        url: `api/sharing_service/${sharing_service_id}/group/${group_id}`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingServiceGroup: build.mutation<
      unknown,
      DeleteSharingServiceGroupArg
    >({
      query: ({ sharing_service_id, group_id }) => ({
        url: `api/sharing_service/${sharing_service_id}/group/${group_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceGroupAutoPublishers: build.mutation<
      unknown,
      SharingServiceGroupAutoPublishersArg
    >({
      query: ({ sharing_service_id, group_id, user_ids = [] }) => ({
        url: `api/sharing_service/${sharing_service_id}/group/${group_id}/auto_publisher`,
        method: "POST",
        body: { user_ids },
      }),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingServiceGroupAutoPublishers: build.mutation<
      unknown,
      SharingServiceGroupAutoPublishersArg
    >({
      query: ({ sharing_service_id, group_id, user_ids = [] }) => ({
        url: `api/sharing_service/${sharing_service_id}/group/${group_id}/auto_publisher`,
        method: "DELETE",
        body: { user_ids },
      }),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceCoauthor: build.mutation<
      unknown,
      SharingServiceCoauthorArg
    >({
      query: ({ sharing_service_id, user_id }) => ({
        url: `api/sharing_service/${sharing_service_id}/coauthor/${user_id}`,
        method: "POST",
      }),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingServiceCoauthor: build.mutation<
      unknown,
      SharingServiceCoauthorArg
    >({
      query: ({ sharing_service_id, user_id }) => ({
        url: `api/sharing_service/${sharing_service_id}/coauthor/${user_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceSubmission: build.mutation<unknown, any>({
      query: (formData) => ({
        url: "api/sharing_service/submission",
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["SharingServiceSubmission"],
    }),
  }),
});

// Websocket: old handler refetched the list on REFRESH_SHARING_SERVICES and
// submissions on REFRESH_SHARING_SERVICE_SUBMISSIONS. The conditional scoping
// (group_id / sharing_service_id) only narrowed *which* fetch ran; invalidating
// the tag refetches whichever query is currently active.
invalidateOnMessage("skyportal/REFRESH_SHARING_SERVICES", () => [
  "SharingService",
]);
invalidateOnMessage("skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS", () => [
  "SharingServiceSubmission",
]);

export const {
  useGetSharingServicesQuery,
  useLazyGetSharingServicesQuery,
  useGetSharingServiceSubmissionsQuery,
  useAddSharingServiceMutation,
  useEditSharingServiceMutation,
  useDeleteSharingServiceMutation,
  useAddSharingServiceGroupMutation,
  useEditSharingServiceGroupMutation,
  useDeleteSharingServiceGroupMutation,
  useAddSharingServiceGroupAutoPublishersMutation,
  useDeleteSharingServiceGroupAutoPublishersMutation,
  useAddSharingServiceCoauthorMutation,
  useDeleteSharingServiceCoauthorMutation,
  useAddSharingServiceSubmissionMutation,
} = sharingServicesApi;
